#!/usr/bin/env python3
"""
ADK Agent — Web Application
============================
Flask web UI that drives the Google ADK-based file-processing agent.
All agent logic lives in adk_agent.py; this file handles only HTTP
endpoints, file management, and SSE log streaming.

Endpoints:
  GET  /                       → web UI (index.html)
  GET  /api/inbox              → list inbox files
  GET  /api/outbox             → list outbox files
  GET  /api/file/inbox/<path>  → read an inbox file
  GET  /api/file/outbox/<path> → read an outbox file
  POST /api/upload             → upload a file to the inbox
  DEL  /api/inbox/<path>       → delete a specific inbox file
  DEL  /api/inbox              → clear all inbox files
  DEL  /api/outbox             → clear all outbox files
  GET  /api/model              → get current model + available models
  POST /api/model              → set active model
  POST /api/agent/run          → start an agent run
  POST /api/agent/reset        → reset agent state to idle
  GET  /api/agent/status       → current status + log snapshot
  GET  /api/agent/logs         → SSE stream of real-time log entries

Environment variables:
  ANTHROPIC_API_KEY   enable Anthropic Claude models
  OPENAI_API_KEY      enable OpenAI GPT models
  OPENROUTER_API_KEY  enable OpenRouter models
  INBOX_DIR           default: ./inbox
  OUTBOX_DIR          default: ./outbox
  PORT                default: 8080
  HOST                default: 0.0.0.0
"""

import json
import logging
import os
import re
import shutil
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

import adk_agent

# ─── Configuration ────────────────────────────────────────────────────────────
INBOX_DIR  = Path(os.environ.get("INBOX_DIR",  "./inbox")).resolve()
OUTBOX_DIR = Path(os.environ.get("OUTBOX_DIR", "./outbox")).resolve()
PORT       = int(os.environ.get("PORT", "8080"))
HOST       = os.environ.get("HOST", "0.0.0.0")

INBOX_DIR.mkdir(parents=True, exist_ok=True)
OUTBOX_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
log = logging.getLogger("web_app")


# ─── Agent State ──────────────────────────────────────────────────────────────
class AgentState:
    """Thread-safe container for one agent run's state and log history."""

    def __init__(self) -> None:
        self._lock       = threading.Lock()
        self.status      = "idle"   # idle | running | completed | error
        self.logs: deque[dict] = deque(maxlen=2000)
        self.started_at: str | None  = None
        self.finished_at: str | None = None
        self.error: str | None       = None
        self._model: str             = adk_agent.default_model()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        with self._lock:
            self.status      = "running"
            self.logs.clear()
            self.started_at  = _now()
            self.finished_at = None
            self.error       = None

    def finish(self, error: str | None = None) -> None:
        with self._lock:
            self.status      = "error" if error else "completed"
            self.finished_at = _now()
            self.error       = error

    def reset(self) -> None:
        with self._lock:
            self.status      = "idle"
            self.logs.clear()
            self.started_at  = None
            self.finished_at = None
            self.error       = None

    # ── Logging ───────────────────────────────────────────────────────────────

    def add_log(self, message: str) -> None:
        with self._lock:
            self.logs.append({"time": _now(), "msg": message})

    def snapshot(self, offset: int = 0) -> dict:
        with self._lock:
            return {
                "status":      self.status,
                "started_at":  self.started_at,
                "finished_at": self.finished_at,
                "error":       self.error,
                "log_count":   len(self.logs),
                "logs":        list(self.logs)[offset:],
            }

    # ── Model ─────────────────────────────────────────────────────────────────

    @property
    def model(self) -> str:
        with self._lock:
            return self._model

    @model.setter
    def model(self, value: str) -> None:
        with self._lock:
            self._model = value


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


state = AgentState()


# ─── Agent Thread ─────────────────────────────────────────────────────────────

def _agent_thread() -> None:
    """Background thread: runs ADK agent, streams output to AgentState."""
    state.start()
    state.add_log("=== Agent run started ===")

    model_id = state.model
    state.add_log(f"model={model_id}")

    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    log_path = OUTBOX_DIR / "agent.log"

    try:
        with log_path.open("w", encoding="utf-8") as log_fh:
            def _log(message: str) -> None:
                if message:
                    state.add_log(message)
                    log_fh.write(message + "\n")
                    log_fh.flush()

            adk_agent.run_agent(
                model_id=model_id,
                inbox=INBOX_DIR,
                outbox=OUTBOX_DIR,
                log_callback=_log,
            )

        state.finish()
        state.add_log("=== Agent run completed successfully ===")

    except Exception as exc:
        err = str(exc)
        log.exception("Agent run failed")
        state.finish(err)
        state.add_log(f"FATAL: {err}")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _safe_path(base: Path, rel: str) -> Path:
    target = (base / rel).resolve()
    if not str(target).startswith(str(base.resolve())):
        raise ValueError(f"Path traversal denied: {rel}")
    return target


def _list_dir(directory: Path) -> list[dict]:
    result = []
    if not directory.exists():
        return result
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            stat = path.stat()
            result.append({
                "name":     str(path.relative_to(directory)),
                "size":     stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            })
    return result


def _sanitise_filename(raw: str) -> str:
    return re.sub(r"[^\w.\-/]", "_", raw)


# ─── Routes: Pages ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ─── Routes: File Browser ─────────────────────────────────────────────────────

@app.route("/api/inbox", methods=["GET"])
def api_list_inbox():
    return jsonify({"files": _list_dir(INBOX_DIR)})


@app.route("/api/outbox", methods=["GET"])
def api_list_outbox():
    return jsonify({"files": _list_dir(OUTBOX_DIR)})


@app.route("/api/file/inbox/<path:filename>", methods=["GET"])
def api_read_inbox(filename):
    try:
        target = _safe_path(INBOX_DIR, filename)
        return jsonify({"name": filename, "content": target.read_text(encoding="utf-8")})
    except (ValueError, FileNotFoundError) as exc:
        return jsonify({"error": str(exc)}), 404


@app.route("/api/file/outbox/<path:filename>", methods=["GET"])
def api_read_outbox(filename):
    try:
        target = _safe_path(OUTBOX_DIR, filename)
        return jsonify({"name": filename, "content": target.read_text(encoding="utf-8")})
    except (ValueError, FileNotFoundError) as exc:
        return jsonify({"error": str(exc)}), 404


# ─── Routes: File Management ──────────────────────────────────────────────────

@app.route("/api/upload", methods=["POST"])
def api_upload():
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    safe_name = _sanitise_filename(file.filename)
    try:
        target = _safe_path(INBOX_DIR, safe_name)
        target.parent.mkdir(parents=True, exist_ok=True)
        file.save(target)
        log.info("Uploaded %s (%d bytes)", safe_name, target.stat().st_size)
        return jsonify({"name": safe_name, "size": target.stat().st_size})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/inbox/<path:filename>", methods=["DELETE"])
def api_delete_inbox(filename):
    try:
        target = _safe_path(INBOX_DIR, filename)
        if target.exists():
            target.unlink()
        return jsonify({"deleted": filename})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/inbox", methods=["DELETE"])
def api_clear_inbox():
    for item in INBOX_DIR.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
    log.info("Inbox cleared")
    return jsonify({"cleared": True})


@app.route("/api/outbox", methods=["DELETE"])
def api_clear_outbox():
    for item in OUTBOX_DIR.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
    log.info("Outbox cleared")
    return jsonify({"cleared": True})


# ─── Routes: Model Selection ──────────────────────────────────────────────────

@app.route("/api/model", methods=["GET"])
def api_get_model():
    available = adk_agent.get_available_models()
    return jsonify({
        "model":   state.model,
        "models":  available,
        "allowed": [m["id"] for m in available],
    })


@app.route("/api/model", methods=["POST"])
def api_set_model():
    data     = request.get_json(silent=True) or {}
    model_id = data.get("model", "")
    allowed  = [m["id"] for m in adk_agent.get_available_models()]
    if model_id not in allowed:
        return jsonify({"error": f"Model not available: {model_id}", "allowed": allowed}), 400
    state.model = model_id
    log.info("Model set to: %s", model_id)
    return jsonify({"model": model_id})


# ─── Routes: Agent Control ────────────────────────────────────────────────────

@app.route("/api/agent/run", methods=["POST"])
def api_run_agent():
    if state.status == "running":
        return jsonify({"error": "Agent is already running"}), 409
    if not (INBOX_DIR / "instruction.md").exists():
        return jsonify({"error": "instruction.md not found in inbox — upload it first"}), 400
    if not adk_agent.get_available_models():
        return jsonify({"error": "No API key configured. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or OPENROUTER_API_KEY"}), 400

    thread = threading.Thread(target=_agent_thread, daemon=True, name="agent")
    thread.start()
    return jsonify({"status": "started"})


@app.route("/api/agent/reset", methods=["POST"])
def api_reset():
    if state.status == "running":
        return jsonify({"error": "Cannot reset while agent is running"}), 409
    state.reset()
    return jsonify({"status": "idle"})


@app.route("/api/agent/status", methods=["GET"])
def api_agent_status():
    offset = int(request.args.get("offset", 0))
    return jsonify(state.snapshot(offset=offset))


# ─── Routes: SSE Log Stream ───────────────────────────────────────────────────

@app.route("/api/agent/logs", methods=["GET"])
def api_agent_logs():
    """Server-Sent Events stream of real-time log entries.

    Each SSE payload is JSON:
      {"time": "...", "msg": "..."}          — a log line
      {"done": true, "status": "completed"}  — final sentinel
    """
    offset = int(request.args.get("offset", 0))

    def _generate():
        sent = offset
        while True:
            snap = state.snapshot(offset=sent)
            for entry in snap["logs"]:
                yield f"data: {json.dumps(entry)}\n\n"
                sent += 1
            if snap["status"] not in ("idle", "running"):
                yield f"data: {json.dumps({'done': True, 'status': snap['status']})}\n\n"
                return
            time.sleep(0.4)

    return Response(
        stream_with_context(_generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    available = adk_agent.get_available_models()

    print(f"\n  ADK Agent Web UI")
    print(f"  ─────────────────────────────────────")
    print(f"  URL    : http://localhost:{PORT}")
    print(f"  Inbox  : {INBOX_DIR}")
    print(f"  Outbox : {OUTBOX_DIR}")
    print(f"  ─────────────────────────────────────")
    if available:
        for m in available:
            marker = "▶" if m["id"] == state.model else " "
            print(f"  {marker} [{m['provider']:10s}] {m['display']}")
    else:
        print("  WARNING: No API key configured.")
        print("  Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or OPENROUTER_API_KEY")
    print()

    app.run(host=HOST, port=PORT, debug=False, threaded=True)


if __name__ == "__main__":
    main()
