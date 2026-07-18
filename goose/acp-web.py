#!/usr/bin/env python3
"""Goose ACP — Flask web UI."""

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import werkzeug.utils
from flask import Flask, Response, abort, jsonify, render_template, request, send_file

PORT_DEFAULT    = 8082
WORKSPACE_DIR   = "workspace"   # created under cwd if it doesn't exist

# ── AcpClient ─────────────────────────────────────────────────────────────────

class AcpClient:
    """JSON-RPC 2.0 client over a goose acp subprocess stdio."""

    def __init__(self, cmd: list[str]):
        self._proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1,
        )
        self._req_id = 0
        self._lock   = threading.Lock()
        self._response_queues: dict[int, queue.Queue] = {}
        self.server_requests: queue.Queue = queue.Queue()
        self.notifications:   queue.Queue = queue.Queue()
        threading.Thread(target=self._read_loop,   daemon=True).start()
        threading.Thread(target=self._stderr_loop, daemon=True).start()

    def _read_loop(self):
        for raw in self._proc.stdout:
            raw = raw.strip()
            if not raw:
                continue
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            msg_id     = msg.get("id")
            has_method = "method" in msg
            if has_method and msg_id is None:
                self.notifications.put(msg)
            elif has_method and msg_id is not None:
                self.server_requests.put(msg)
            elif msg_id is not None:
                with self._lock:
                    q = self._response_queues.get(msg_id)
                if q:
                    q.put(msg)

    def _stderr_loop(self):
        for _ in self._proc.stderr:
            pass

    def request(self, method: str, params: Optional[dict] = None,
                timeout: float = 60.0,
                on_notification=None, on_server_request=None) -> dict:
        with self._lock:
            self._req_id += 1
            req_id = self._req_id
            q: queue.Queue = queue.Queue()
            self._response_queues[req_id] = q

        msg: dict = {"jsonrpc": "2.0", "method": method, "id": req_id}
        if params:
            msg["params"] = params
        self._proc.stdin.write(json.dumps(msg) + "\n")
        self._proc.stdin.flush()

        deadline = time.monotonic() + timeout
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return {"error": {"code": -32000, "message": "Timed out"}}
                self._drain(on_notification, on_server_request)
                try:
                    resp = q.get(timeout=min(remaining, 0.05))
                    # Drain any notifications that arrived alongside the final response
                    # so all streaming chunks reach event_q before we return.
                    self._drain(on_notification, None)
                    return resp
                except queue.Empty:
                    continue
        finally:
            with self._lock:
                self._response_queues.pop(req_id, None)

    def _drain(self, on_notification=None, on_server_request=None):
        while True:
            try:
                msg = self.notifications.get_nowait()
                if on_notification:
                    on_notification(msg)
            except queue.Empty:
                break
        while True:
            try:
                msg = self.server_requests.get_nowait()
                if on_server_request:
                    on_server_request(msg)
            except queue.Empty:
                break

    def reply(self, req_id: int, result: dict):
        msg = {"jsonrpc": "2.0", "id": req_id, "result": result}
        self._proc.stdin.write(json.dumps(msg) + "\n")
        self._proc.stdin.flush()

    def notify(self, method: str, params: Optional[dict] = None):
        msg: dict = {"jsonrpc": "2.0", "method": method}
        if params:
            msg["params"] = params
        self._proc.stdin.write(json.dumps(msg) + "\n")
        self._proc.stdin.flush()

    def close(self):
        try:
            self._proc.terminate()
            self._proc.wait(timeout=5)
        except Exception:
            pass

    @property
    def alive(self) -> bool:
        return self._proc.poll() is None


# ── GooseWebSession ───────────────────────────────────────────────────────────

class GooseWebSession:
    def __init__(self, builtin: str = "developer"):
        self._builtin    = builtin
        self._lock       = threading.Lock()
        self.client: Optional[AcpClient] = None
        self.session_id: Optional[str]   = None
        self.cwd         = os.getcwd()
        self.provider    = "?"
        self.model       = "?"
        self.mode        = "auto"
        self._busy       = False
        self._init_error: Optional[str] = None
        self.available_commands: list    = []
        # Permission synchronisation
        self._perm_event  = threading.Event()
        self._perm_choice: Optional[str] = None

    # ── Config ────────────────────────────────────────────────────────────────

    def _load_goose_config(self):
        cfg = Path.home() / ".config" / "goose" / "config.yaml"
        try:
            for line in cfg.read_text().splitlines():
                line = line.strip()
                if line.startswith("active_provider:"):
                    self.provider = line.split(":", 1)[1].strip()
                elif line.startswith("model:"):
                    self.model = line.split(":", 1)[1].strip()
        except Exception:
            pass

    # ── Session lifecycle ─────────────────────────────────────────────────────

    def start(self, cwd: Optional[str] = None):
        with self._lock:
            if self.client:
                try:
                    self.client.close()
                except Exception:
                    pass
                self.client = None

            if cwd:
                resolved = Path(cwd).expanduser().resolve()
                resolved.mkdir(parents=True, exist_ok=True)
                self.cwd = str(resolved)

            self._load_goose_config()
            self._init_error = None

            cmd = ["goose", "acp", "--with-builtin", self._builtin]
            client = AcpClient(cmd)

            resp = client.request("initialize", {
                "protocolVersion": "v1",
                "clientCapabilities": {},
                "clientInfo": {"name": "goose-web", "version": "1.0.0"},
            })
            if "error" in resp:
                client.close()
                self._init_error = resp["error"].get("message", str(resp["error"]))
                raise RuntimeError(f"Initialize failed: {self._init_error}")

            resp = client.request("session/new", {"cwd": self.cwd, "mcpServers": []})
            if "error" in resp:
                client.close()
                self._init_error = resp["error"].get("message", str(resp["error"]))
                raise RuntimeError(f"Session/new failed: {self._init_error}")

            self.client     = client
            self.session_id = resp.get("result", {}).get("sessionId", "unknown")

            # Drain any startup notifications (e.g. available_commands_update)
            time.sleep(0.2)
            client._drain(on_notification=self._handle_bg_notification)

            # Default to auto mode so tools are enabled
            self._set_mode_locked("auto", client)

    # ── Background notification handler ──────────────────────────────────────

    def _handle_bg_notification(self, msg):
        update = msg.get("params", {}).get("update", {})
        kind   = update.get("sessionUpdate", "")
        if kind in ("available_commands", "available_commands_update"):
            self.available_commands = [
                {
                    "name":        c.get("name", ""),
                    "description": c.get("description", ""),
                    "inputHint":   c.get("inputHint", ""),
                }
                for c in update.get("commands", [])
            ]
        elif kind == "mode_change":
            mode = update.get("mode", {})
            self.mode = mode.get("name", "") if isinstance(mode, dict) else str(mode)

    # ── Mode switching ────────────────────────────────────────────────────────

    def _set_mode_locked(self, mode: str, client: AcpClient):
        resp = client.request("session/set_mode", {
            "sessionId": self.session_id,
            "mode": mode,
        })
        if "error" not in resp:
            self.mode = mode

    def set_mode(self, mode: str):
        if not self.client or not self.client.alive:
            raise RuntimeError("Session not ready")
        self._set_mode_locked(mode, self.client)

    # ── Streaming prompt ──────────────────────────────────────────────────────

    def prompt_stream(self, text: str):
        """Generator that yields SSE-formatted strings."""
        if self._busy:
            yield _sse({"type": "error", "message": "Agent is busy — please wait."})
            return
        if not self.client or not self.client.alive:
            yield _sse({"type": "error", "message": "Session not ready. Click Reconnect."})
            return

        self._busy  = True
        event_q: queue.Queue = queue.Queue()

        def on_notification(msg):
            update = msg.get("params", {}).get("update", {})
            kind   = update.get("sessionUpdate", "")
            if kind == "agent_message_chunk":
                text = update.get("content", {}).get("text", "")
                if text:
                    event_q.put({"type": "chunk", "text": text})
            elif kind == "tool_call":
                event_q.put({
                    "type":  "tool",
                    "id":    update.get("toolCallId", ""),
                    "title": update.get("title", "tool"),
                })
            elif kind == "tool_call_update":
                event_q.put({
                    "type":   "tool_done",
                    "id":     update.get("toolCallId", ""),
                    "status": update.get("status", ""),
                })
            elif kind == "mode_change":
                mode = update.get("mode", {})
                name = mode.get("name", "") if isinstance(mode, dict) else str(mode)
                self.mode = name
                event_q.put({"type": "mode_change", "mode": name})
            elif kind in ("available_commands", "available_commands_update"):
                commands = update.get("commands", [])
                parsed = [
                    {
                        "name":        c.get("name", ""),
                        "description": c.get("description", ""),
                        "inputHint":   c.get("inputHint", ""),
                    }
                    for c in commands
                ]
                self.available_commands = parsed
                event_q.put({"type": "commands", "commands": parsed})

        def on_server_request(msg):
            method = msg.get("method", "")
            if method not in ("session/request_permission", "requestPermission"):
                return
            req_id  = msg.get("id")
            params  = msg.get("params", {})
            tc      = params.get("toolCall", {})
            options = params.get("options", [])
            raw_in  = tc.get("rawInput", {})

            event_q.put({
                "type":     "permission",
                "req_id":   req_id,
                "title":    tc.get("title", "Unknown operation"),
                "rawInput": (json.dumps(raw_in) if isinstance(raw_in, dict) else str(raw_in))[:400],
                "options":  options,
            })

            self._perm_event.clear()
            self._perm_choice = None
            if not self._perm_event.wait(timeout=120):
                # Timed out — default to second option (allow_once) or first
                self._perm_choice = (options[1].get("optionId", "allow_once")
                                     if len(options) > 1 else "allow_once")

            choice = self._perm_choice or "allow_once"
            if self.client:
                self.client.reply(req_id, {"outcome": {"type": "selected", "optionId": choice}})

        def run():
            try:
                resp = self.client.request(
                    "session/prompt",
                    {"sessionId": self.session_id,
                     "prompt": [{"type": "text", "text": text}]},
                    timeout=300.0,
                    on_notification=on_notification,
                    on_server_request=on_server_request,
                )
                if "error" in resp:
                    event_q.put({"type": "error",
                                 "message": resp["error"].get("message", "Unknown error")})
                else:
                    event_q.put({"type": "done",
                                 "stopReason": resp.get("result", {}).get("stopReason", "")})
            except Exception as exc:
                event_q.put({"type": "error", "message": str(exc)})
            finally:
                self._busy = False

        threading.Thread(target=run, daemon=True).start()

        while True:
            try:
                evt = event_q.get(timeout=30)
                yield _sse(evt)
                if evt["type"] in ("done", "error"):
                    break
            except queue.Empty:
                yield "data: {\"type\":\"ping\"}\n\n"

    # ── Permission / cancel ───────────────────────────────────────────────────

    def respond_permission(self, option_id: str):
        self._perm_choice = option_id
        self._perm_event.set()

    def cancel(self):
        if self.client and self.session_id:
            self.client.notify("session/cancel", {"sessionId": self.session_id})

    # ── File operations ───────────────────────────────────────────────────────

    def _safe_path(self, rel: str) -> Optional[Path]:
        base   = Path(self.cwd).resolve()
        target = (base / rel).resolve()
        return target if str(target).startswith(str(base)) else None

    def list_files(self, rel_path: str = "") -> list[dict]:
        base   = Path(self.cwd).resolve()
        target = self._safe_path(rel_path) if rel_path else base
        if target is None or not target.is_dir():
            return []
        items = []
        try:
            entries = sorted(target.iterdir(),
                             key=lambda p: (not p.is_dir(), p.name.lower()))
            for p in entries:
                try:
                    size = p.stat().st_size if p.is_file() else 0
                except OSError:
                    size = 0
                items.append({
                    "name":   p.name,
                    "path":   str(p.relative_to(base)),
                    "is_dir": p.is_dir(),
                    "size":   size,
                })
        except PermissionError:
            pass
        return items

    def upload(self, files, rel_dir: str = "") -> tuple[list, list]:
        dest_dir = self._safe_path(rel_dir) if rel_dir else Path(self.cwd)
        if dest_dir is None:
            return [], [f.filename for f in files]
        dest_dir.mkdir(parents=True, exist_ok=True)
        uploaded, errors = [], []
        for f in files:
            if not f.filename:
                continue
            safe = werkzeug.utils.secure_filename(f.filename)
            try:
                f.save(str(dest_dir / safe))
                uploaded.append(safe)
            except Exception:
                errors.append(f.filename)
        return uploaded, errors

    def delete(self, rel: str):
        p = self._safe_path(rel)
        if p is None:
            raise ValueError("Invalid path")
        if not p.exists():
            raise FileNotFoundError(rel)
        if p.is_dir():
            shutil.rmtree(str(p))
        else:
            p.unlink()

    def mkdir(self, rel_parent: str, name: str):
        base = self._safe_path(rel_parent) if rel_parent else Path(self.cwd)
        if base is None:
            raise ValueError("Invalid parent path")
        safe = werkzeug.utils.secure_filename(name)
        if not safe:
            raise ValueError("Invalid folder name")
        (base / safe).mkdir(parents=True, exist_ok=True)

    # ── Status ────────────────────────────────────────────────────────────────

    @property
    def status(self) -> dict:
        return {
            "provider":   self.provider,
            "model":      self.model,
            "mode":       self.mode,
            "session_id": self.session_id,
            "cwd":        self.cwd,
            "busy":       self._busy,
            "alive":      self.client.alive if self.client else False,
            "error":      self._init_error,
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


# ── Flask app ─────────────────────────────────────────────────────────────────

app     = Flask(__name__)
_session = GooseWebSession()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    return jsonify(_session.status)


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    text = (data.get("message") or "").strip()
    if not text:
        return jsonify({"error": "Empty message"}), 400

    return Response(
        _session.prompt_stream(text),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/permission", methods=["POST"])
def api_permission():
    data      = request.get_json(silent=True) or {}
    option_id = (data.get("option_id") or "allow_once").strip()
    _session.respond_permission(option_id)
    return jsonify({"ok": True})


@app.route("/api/cancel", methods=["POST"])
def api_cancel():
    _session.cancel()
    return jsonify({"ok": True})


@app.route("/api/reconnect", methods=["POST"])
def api_reconnect():
    data = request.get_json(silent=True) or {}
    cwd  = (data.get("cwd") or "").strip() or None
    try:
        _session.start(cwd=cwd)
        return jsonify({"ok": True, **_session.status})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/cwd", methods=["POST"])
def api_set_cwd():
    data = request.get_json(silent=True) or {}
    cwd  = (data.get("cwd") or "").strip()
    if not cwd:
        return jsonify({"error": "No path provided"}), 400
    try:
        _session.start(cwd=cwd)
        return jsonify({"ok": True, **_session.status})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/files")
def api_files():
    rel = request.args.get("path", "")
    return jsonify({
        "files": _session.list_files(rel),
        "cwd":   _session.cwd,
        "path":  rel,
    })


@app.route("/api/upload", methods=["POST"])
def api_upload():
    rel_dir  = request.form.get("path", "")
    uploaded, errors = _session.upload(request.files.getlist("files"), rel_dir)
    return jsonify({"uploaded": uploaded, "errors": errors})


@app.route("/api/download")
def api_download():
    rel = request.args.get("path", "")
    if not rel:
        abort(400)
    p = _session._safe_path(rel)
    if p is None or not p.is_file():
        abort(404)
    return send_file(str(p), as_attachment=True, download_name=p.name)


@app.route("/api/delete", methods=["DELETE"])
def api_delete():
    data = request.get_json(silent=True) or {}
    rel  = (data.get("path") or "").strip()
    if not rel:
        return jsonify({"error": "No path"}), 400
    try:
        _session.delete(rel)
        return jsonify({"ok": True})
    except FileNotFoundError:
        return jsonify({"error": "Not found"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/commands")
def api_commands():
    return jsonify({"commands": _session.available_commands})


@app.route("/api/setmode", methods=["POST"])
def api_setmode():
    data = request.get_json(silent=True) or {}
    mode = (data.get("mode") or "").strip()
    if not mode:
        return jsonify({"error": "No mode provided"}), 400
    try:
        _session.set_mode(mode)
        return jsonify({"ok": True, "mode": _session.mode})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/mkdir", methods=["POST"])
def api_mkdir():
    data   = request.get_json(silent=True) or {}
    parent = (data.get("parent") or "").strip()
    name   = (data.get("name")   or "").strip()
    if not name:
        return jsonify({"error": "No name"}), 400
    try:
        _session.mkdir(parent, name)
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


# ── Banner / main ─────────────────────────────────────────────────────────────

def _print_banner(port: int):
    print(f"\n  Goose ACP Web UI")
    print(f"  {'─'*44}")
    print(f"  URL      : http://localhost:{port}")
    print(f"  Provider : {_session.provider}")
    print(f"  Model    : {_session.model}")
    print(f"  CWD      : {_session.cwd}")
    print(f"  {'─'*44}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Goose ACP Web UI")
    parser.add_argument("--port",    "-p", type=int,  default=PORT_DEFAULT)
    parser.add_argument("--builtin", "-b", default="developer",
                        metavar="NAME[,NAME…]",
                        help="Builtin extensions (default: developer)")
    parser.add_argument("--cwd",     "-C", default=os.getcwd(),
                        metavar="PATH", help="Initial working directory")
    parser.add_argument("--goose",         default="goose",
                        metavar="CMD",  help="Path to goose executable")
    args = parser.parse_args()

    _session._builtin = args.builtin

    # Default CWD is ./workspace next to this script; create if absent
    default_ws = Path(__file__).parent / WORKSPACE_DIR
    raw_cwd    = Path(args.cwd).expanduser().resolve() if args.cwd != os.getcwd() else default_ws
    raw_cwd.mkdir(parents=True, exist_ok=True)
    _session.cwd = str(raw_cwd)

    print(f"  Starting goose acp…", flush=True)
    ready = threading.Event()

    def _start():
        try:
            _session.start()
        except Exception as exc:
            print(f"  Warning: {exc}", file=sys.stderr)
        finally:
            ready.set()

    threading.Thread(target=_start, daemon=True).start()
    ready.wait(timeout=20)
    _print_banner(args.port)

    app.run(host="0.0.0.0", port=args.port, debug=False, threaded=True)
