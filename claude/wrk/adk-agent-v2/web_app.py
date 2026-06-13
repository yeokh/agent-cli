#!/usr/bin/env python3
"""
ADK Agent Harness -- Flask Web Server

Web UI for the Google ADK file-processing harness.  All agent logic lives in
adk_agent.py; this file handles HTTP endpoints, file management, settings,
and SSE log streaming.

Folders (editable via the UI):
  agent/   instruction.md (required) + skill .md files
  input/   job payload files
  output/  agent results + agent.log (read-only in the UI)

Endpoints -- see PROJECT-SPEC.md section 6.3 for the full API table.

Environment variables:
  ANTHROPIC_API_KEY    Anthropic provider key
  OPENROUTER_API_KEY   OpenRouter provider key
  OPENAI_API_KEY       OpenAI-compatible provider key (optional for local)
  OPENAI_BASE_URL      OpenAI-compatible endpoint (default http://localhost:11434/v1)
  API_PROVIDER         anthropic | openrouter | openai-compatible
  MODEL                model id (default claude-opus-4-5)
  MAX_TURNS            max agentic loop iterations (default 50)
  AGENT_DIR / INPUT_DIR / OUTPUT_DIR   folder overrides
  PORT / HOST          web server bind (default 8080 / 0.0.0.0)
"""

import asyncio
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

import httpx
from flask import Flask, Response, jsonify, render_template, request, stream_with_context

import adk_agent

# --- Configuration ------------------------------------------------------------

AGENT_DIR = Path(os.environ.get("AGENT_DIR", "./agent")).resolve()
INPUT_DIR = Path(os.environ.get("INPUT_DIR", "./input")).resolve()
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "./output")).resolve()
PORT = int(os.environ.get("PORT", "8080"))
HOST = os.environ.get("HOST", "0.0.0.0")

for d in (AGENT_DIR, INPUT_DIR, OUTPUT_DIR):
    d.mkdir(parents=True, exist_ok=True)

FOLDERS = {"agent": AGENT_DIR, "input": INPUT_DIR, "output": OUTPUT_DIR}
EDITABLE_FOLDERS = ("agent", "input")

JOB_HISTORY_FILE = OUTPUT_DIR / ".job_history.json"
JOB_HISTORY_MAX = 20
HIDDEN_FILES = {".job_history.json", ".gitkeep"}

KEY_ENV_VARS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "openai-compatible": "OPENAI_API_KEY",
}

app = Flask(__name__)
log = logging.getLogger("web_app")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Agent State --------------------------------------------------------------

class AgentState:
    """Thread-safe container for one agent run's state, logs, and metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.status = "idle"  # idle | running | completed | error
        self.logs: deque[dict] = deque(maxlen=2000)
        self.started_at: str | None = None
        self.finished_at: str | None = None
        self.error: str | None = None
        self.metrics: dict | None = None

    def start(self) -> None:
        with self._lock:
            self.status = "running"
            self.logs.clear()
            self.started_at = _now()
            self.finished_at = None
            self.error = None
            self.metrics = None

    def finish(self, error: str | None = None, stats: dict | None = None) -> None:
        with self._lock:
            self.status = "error" if error else "completed"
            self.finished_at = _now()
            self.error = error
            self.metrics = self._build_metrics(stats or {})

    def _build_metrics(self, stats: dict) -> dict:
        duration = None
        if self.started_at and self.finished_at:
            duration = (
                datetime.fromisoformat(self.finished_at)
                - datetime.fromisoformat(self.started_at)
            ).total_seconds()
        return {
            "duration_seconds": duration,
            "total_turns": stats.get("total_turns"),
            "total_cost_usd": stats.get("total_cost_usd"),
            "total_input_tokens": stats.get("total_input_tokens"),
            "total_output_tokens": stats.get("total_output_tokens"),
            "log_lines": len(self.logs),
            "output_files": _count_output_files(),
            "status": self.status,
        }

    def reset(self) -> None:
        with self._lock:
            self.status = "idle"
            self.logs.clear()
            self.started_at = None
            self.finished_at = None
            self.error = None
            self.metrics = None

    def add_log(self, message: str) -> None:
        with self._lock:
            self.logs.append({"time": _now(), "msg": message})

    def snapshot(self, offset: int = 0) -> dict:
        with self._lock:
            return {
                "status": self.status,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "error": self.error,
                "metrics": self.metrics,
                "log_count": len(self.logs),
                "logs": list(self.logs)[offset:],
            }


state = AgentState()


def _count_output_files() -> int:
    if not OUTPUT_DIR.exists():
        return 0
    return sum(
        1 for p in OUTPUT_DIR.rglob("*")
        if p.is_file() and p.name not in HIDDEN_FILES and p.name != "agent.log"
    )


# --- Job History --------------------------------------------------------------

def _append_job_history(snap: dict) -> None:
    """Append one run record to output/.job_history.json (cap at 20 entries)."""
    metrics = snap.get("metrics") or {}
    entry = {
        "run_id": snap.get("started_at"),
        "status": snap.get("status"),
        "provider": os.environ.get("API_PROVIDER", "anthropic"),
        "model": os.environ.get("MODEL", adk_agent.DEFAULT_MODEL),
        "duration_seconds": metrics.get("duration_seconds"),
        "total_turns": metrics.get("total_turns"),
        "total_cost_usd": metrics.get("total_cost_usd"),
        "total_input_tokens": metrics.get("total_input_tokens"),
        "total_output_tokens": metrics.get("total_output_tokens"),
        "log_lines": metrics.get("log_lines"),
        "output_files": metrics.get("output_files"),
    }
    history: list = []
    try:
        if JOB_HISTORY_FILE.exists():
            history = json.loads(JOB_HISTORY_FILE.read_text(encoding="utf-8"))
            if not isinstance(history, list):
                history = []
    except (json.JSONDecodeError, OSError):
        history = []
    history.append(entry)
    history = history[-JOB_HISTORY_MAX:]
    try:
        JOB_HISTORY_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")
    except OSError as exc:
        log.warning("Could not write job history: %s", exc)


# --- Agent Thread -------------------------------------------------------------

def _agent_thread() -> None:
    """Background thread: runs the ADK agent and streams output to AgentState."""
    stats_out: dict = {}
    state.start()
    state.add_log("=== Agent run started ===")

    log_path = OUTPUT_DIR / "agent.log"
    try:
        with log_path.open("w", encoding="utf-8") as log_fh:

            def _log(message: str) -> None:
                if message:
                    state.add_log(message)
                    log_fh.write(message + "\n")
                    log_fh.flush()

            asyncio.run(
                adk_agent.run_agent(AGENT_DIR, INPUT_DIR, OUTPUT_DIR, _log, stats_out)
            )

        state.finish(stats=stats_out)
        state.add_log("=== Agent run completed successfully ===")
    except FileNotFoundError as exc:
        state.finish(str(exc))
        state.add_log(f"FATAL: {exc}")
    except RuntimeError as exc:
        state.finish(str(exc))
        state.add_log(f"BLOCKED: {exc}")
    except Exception as exc:
        log.exception("Agent run failed")
        state.finish(f"Unexpected error: {exc}")
        state.add_log(f"FATAL: Unexpected error: {exc}")

    _append_job_history(state.snapshot())


# --- Path Helpers -------------------------------------------------------------

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
        if not path.is_file() or path.name in HIDDEN_FILES:
            continue
        stat = path.stat()
        result.append({
            "name": str(path.relative_to(directory)).replace("\\", "/"),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        })
    return result


def _sanitise_filename(raw: str) -> str:
    return re.sub(r"[^\w.\-/]", "_", raw)


def _folder_or_404(folder: str, editable_only: bool = False):
    if folder not in FOLDERS:
        return None
    if editable_only and folder not in EDITABLE_FOLDERS:
        return None
    return FOLDERS[folder]


# --- Routes: Pages ------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# --- Routes: File Browser & Editor --------------------------------------------

@app.route("/api/<any('agent','input','output'):folder>", methods=["GET"])
def api_list_folder(folder):
    return jsonify({"files": _list_dir(FOLDERS[folder])})


@app.route("/api/file/<any('agent','input','output'):folder>/<path:filename>", methods=["GET"])
def api_read_file(folder, filename):
    try:
        target = _safe_path(FOLDERS[folder], filename)
        if not target.is_file():
            return jsonify({"error": f"File not found: {filename}"}), 404
        return jsonify({
            "name": filename,
            "content": target.read_text(encoding="utf-8", errors="replace"),
        })
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404


@app.route("/api/file/<any('agent','input'):folder>/<path:filename>", methods=["PUT"])
def api_save_file(folder, filename):
    data = request.get_json(silent=True) or {}
    if "content" not in data:
        return jsonify({"error": "Missing 'content'"}), 400
    try:
        target = _safe_path(FOLDERS[folder], filename)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data["content"], encoding="utf-8")
        return jsonify({"name": filename, "size": target.stat().st_size})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/file/<any('agent','input'):folder>", methods=["POST"])
def api_create_file(folder):
    data = request.get_json(silent=True) or {}
    name = _sanitise_filename(data.get("name", "").strip())
    if not name:
        return jsonify({"error": "Missing or invalid 'name'"}), 400
    try:
        target = _safe_path(FOLDERS[folder], name)
        if target.exists():
            return jsonify({"error": f"File already exists: {name}"}), 409
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data.get("content", ""), encoding="utf-8")
        return jsonify({"name": name, "size": target.stat().st_size})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/upload/<any('agent','input'):folder>", methods=["POST"])
def api_upload(folder):
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400
    safe_name = _sanitise_filename(file.filename)
    try:
        target = _safe_path(FOLDERS[folder], safe_name)
        target.parent.mkdir(parents=True, exist_ok=True)
        file.save(target)
        log.info("Uploaded %s/%s (%d bytes)", folder, safe_name, target.stat().st_size)
        return jsonify({"name": safe_name, "size": target.stat().st_size})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/file/<any('agent','input'):folder>/<path:filename>", methods=["DELETE"])
def api_delete_file(folder, filename):
    try:
        target = _safe_path(FOLDERS[folder], filename)
        if target.exists():
            target.unlink()
        return jsonify({"deleted": filename})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/<any('agent','input','output'):folder>", methods=["DELETE"])
def api_clear_folder(folder):
    base = FOLDERS[folder]
    for item in base.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
    log.info("%s cleared", folder)
    return jsonify({"cleared": True})


# --- Routes: Provider & Model -------------------------------------------------

_model_cache: dict[str, tuple[float, list]] = {}
_model_cache_lock = threading.Lock()
_MODEL_CACHE_TTL = 300.0


def _fetch_models(provider: str) -> list[dict]:
    """Fetch the live model list for provider with a 5-minute cache."""
    with _model_cache_lock:
        cached = _model_cache.get(provider)
        if cached and time.monotonic() - cached[0] < _MODEL_CACHE_TTL:
            return cached[1]

    models: list[dict] = []
    try:
        if provider == "anthropic":
            key = os.environ.get("ANTHROPIC_API_KEY", "")
            if key:
                resp = httpx.get(
                    "https://api.anthropic.com/v1/models",
                    headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                    timeout=10,
                )
                resp.raise_for_status()
                models = [
                    {"id": m["id"], "name": m.get("display_name", m["id"])}
                    for m in resp.json().get("data", [])
                ]
        elif provider == "openrouter":
            key = os.environ.get("OPENROUTER_API_KEY", "")
            if key:
                resp = httpx.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {key}"},
                    timeout=15,
                )
                resp.raise_for_status()
                models = [
                    {"id": m["id"], "name": m.get("name", m["id"])}
                    for m in resp.json().get("data", [])
                    if "tools" in (m.get("supported_parameters") or [])
                ]
        elif provider == "openai-compatible":
            base = os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1").rstrip("/")
            headers = {}
            key = os.environ.get("OPENAI_API_KEY", "")
            if key:
                headers["Authorization"] = f"Bearer {key}"
            resp = httpx.get(f"{base}/models", headers=headers, timeout=10)
            resp.raise_for_status()
            models = [
                {"id": m["id"], "name": m["id"]}
                for m in resp.json().get("data", [])
            ]
    except Exception as exc:
        log.warning("Failed to fetch %s models: %s", provider, exc)

    with _model_cache_lock:
        _model_cache[provider] = (time.monotonic(), models)
    return models


@app.route("/api/providers", methods=["GET"])
def api_providers():
    return jsonify({
        "providers": list(adk_agent.PROVIDERS),
        "current": os.environ.get("API_PROVIDER", "anthropic"),
    })


@app.route("/api/provider", methods=["GET"])
def api_get_provider():
    return jsonify({"provider": os.environ.get("API_PROVIDER", "anthropic")})


@app.route("/api/provider", methods=["POST"])
def api_set_provider():
    data = request.get_json(silent=True) or {}
    provider = data.get("provider", "")
    if provider not in adk_agent.PROVIDERS:
        return jsonify({"error": f"Unknown provider: {provider}"}), 400
    os.environ["API_PROVIDER"] = provider
    log.info("Provider set to: %s", provider)
    return jsonify({"provider": provider})


@app.route("/api/models", methods=["GET"])
def api_models():
    provider = request.args.get("provider") or os.environ.get("API_PROVIDER", "anthropic")
    if provider not in adk_agent.PROVIDERS:
        return jsonify({"error": f"Unknown provider: {provider}"}), 400
    return jsonify({"models": _fetch_models(provider), "provider": provider})


@app.route("/api/model", methods=["GET"])
def api_get_model():
    return jsonify({
        "model": os.environ.get("MODEL", adk_agent.DEFAULT_MODEL),
        "provider": os.environ.get("API_PROVIDER", "anthropic"),
    })


@app.route("/api/model", methods=["POST"])
def api_set_model():
    data = request.get_json(silent=True) or {}
    model = data.get("model", "").strip()
    if not model:
        return jsonify({"error": "Missing 'model'"}), 400
    os.environ["MODEL"] = model
    log.info("Model set to: %s", model)
    return jsonify({"model": model})


# --- Routes: API Key Management -----------------------------------------------
#
# Keys live only in this process's environment.  GET /api/keys reports
# presence as booleans only -- keys are never returned to the browser.

@app.route("/api/keys", methods=["GET"])
def api_get_keys():
    return jsonify({
        provider: bool(os.environ.get(env_var))
        for provider, env_var in KEY_ENV_VARS.items()
    })


@app.route("/api/keys", methods=["POST"])
def api_set_key():
    data = request.get_json(silent=True) or {}
    provider = data.get("provider", "")
    key = data.get("key", "")
    if provider not in KEY_ENV_VARS:
        return jsonify({"error": f"Unknown provider: {provider}"}), 400
    if not key:
        return jsonify({"error": "Missing 'key'"}), 400
    os.environ[KEY_ENV_VARS[provider]] = key
    with _model_cache_lock:
        _model_cache.pop(provider, None)
    log.info("API key set for provider: %s", provider)
    return jsonify({"ok": True})


# --- Routes: Settings ---------------------------------------------------------

@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    return jsonify({
        "max_turns": int(os.environ.get("MAX_TURNS", "50") or 50),
        "allow_shell": os.environ.get("ALLOW_SHELL", "true").lower() not in ("0", "false", "no", "off"),
        "shell_timeout": int(os.environ.get("SHELL_TIMEOUT", "60") or 60),
        "openai_base_url": os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1"),
    })


@app.route("/api/settings", methods=["POST"])
def api_set_settings():
    data = request.get_json(silent=True) or {}
    if "max_turns" in data:
        try:
            os.environ["MAX_TURNS"] = str(max(1, int(data["max_turns"])))
        except (TypeError, ValueError):
            return jsonify({"error": "max_turns must be an integer"}), 400
    if "allow_shell" in data:
        os.environ["ALLOW_SHELL"] = "true" if data["allow_shell"] else "false"
    if "shell_timeout" in data:
        try:
            os.environ["SHELL_TIMEOUT"] = str(max(1, int(data["shell_timeout"])))
        except (TypeError, ValueError):
            return jsonify({"error": "shell_timeout must be an integer"}), 400
    if "openai_base_url" in data:
        os.environ["OPENAI_BASE_URL"] = str(data["openai_base_url"]).strip()
        with _model_cache_lock:
            _model_cache.pop("openai-compatible", None)
    return api_get_settings()


# --- Routes: Job History ------------------------------------------------------

@app.route("/api/jobs", methods=["GET"])
def api_jobs():
    try:
        if JOB_HISTORY_FILE.exists():
            jobs = json.loads(JOB_HISTORY_FILE.read_text(encoding="utf-8"))
        else:
            jobs = []
    except (json.JSONDecodeError, OSError):
        jobs = []
    return jsonify({"jobs": jobs})


# --- Routes: Agent Control ----------------------------------------------------

@app.route("/api/agent/run", methods=["POST"])
def api_run_agent():
    if state.status == "running":
        return jsonify({"error": "Agent is already running"}), 409
    if not (AGENT_DIR / "instruction.md").exists():
        return jsonify({"error": "instruction.md not found in agent/ -- create it first"}), 400

    provider = os.environ.get("API_PROVIDER", "anthropic")
    env_var = KEY_ENV_VARS[provider]
    if provider != "openai-compatible" and not os.environ.get(env_var):
        return jsonify({"error": f"No API key configured for {provider}. Set {env_var}."}), 400

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


# --- Routes: SSE Log Stream ---------------------------------------------------

@app.route("/api/agent/logs", methods=["GET"])
def api_agent_logs():
    """Server-Sent Events stream of real-time log entries.

    Each SSE payload is JSON:
      {"time": "...", "msg": "..."}          -- a log line
      {"done": true, "status": "completed"}  -- final sentinel
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


# --- Entry Point --------------------------------------------------------------

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    provider = os.environ.get("API_PROVIDER", "anthropic")
    model = os.environ.get("MODEL", adk_agent.DEFAULT_MODEL)

    # ASCII-only banner: Windows consoles often default to cp1252.
    print()
    print("  ADK Agent Harness - Web UI")
    print("  ----------------------------------")
    print(f"  URL      : http://localhost:{PORT}")
    print(f"  Provider : {provider}")
    print(f"  Model    : {model}")
    print(f"  Agent    : {AGENT_DIR}")
    print(f"  Input    : {INPUT_DIR}")
    print(f"  Output   : {OUTPUT_DIR}")
    print("  ----------------------------------")
    missing = [
        env for prov, env in KEY_ENV_VARS.items()
        if prov != "openai-compatible" and not os.environ.get(env)
    ]
    if len(missing) == 2:
        print("  NOTE: no API key set -- add one via the web UI or environment.")
    print()

    app.run(host=HOST, port=PORT, debug=False, threaded=True)


if __name__ == "__main__":
    main()
