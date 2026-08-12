#!/usr/bin/env python3
"""
Goose ACP HTTP+SSE bridge server.

Spawns 'goose acp' as a subprocess and exposes it over HTTP so that
a standalone client can connect from anywhere on the network.

Endpoints
─────────
  GET  /health                   liveness check
  GET  /info                     agent info (provider, model, cmd)
  GET  /events                   SSE stream — notifications, server-initiated requests,
                                 and file_created events when goose writes new files
  POST /rpc                      forward a JSON-RPC request; returns the response
  POST /reply                    forward a client reply to a server-initiated request
  POST /notify                   forward a JSON-RPC notification (fire-and-forget)
  POST /files/<session_id>       upload a file into the session transfer area
  GET  /files/<session_id>       list files in the session transfer area
  GET  /files/<session_id>/<fn>  download a file from the session transfer area

Transfer area
─────────────
Each session gets a private temporary directory (the "transfer area") created on
session/new. Files uploaded by the client and files written by goose into this
directory live here. The area is deleted automatically when the server exits.
Goose still operates in the cwd the client requested; to have goose write output
to the transfer area the client should include the transferDir path in the prompt.
"""

import argparse
import atexit
import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

try:
    from flask import Flask, Response, jsonify, send_file
    from flask import request as flask_request
    from flask import stream_with_context
except ImportError:
    sys.exit("Flask is required:  pip install flask")

try:
    from werkzeug.utils import secure_filename
except ImportError:
    sys.exit("Werkzeug is required:  pip install werkzeug")


# ── Goose config ──────────────────────────────────────────────────────────────

def _goose_config() -> tuple[str, str]:
    cfg_path = Path.home() / ".config" / "goose" / "config.yaml"
    try:
        provider = model = "?"
        for line in cfg_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("active_provider:"):
                provider = line.split(":", 1)[1].strip()
            elif line.startswith("model:"):
                model = line.split(":", 1)[1].strip()
        return provider, model
    except Exception:
        return "?", "?"


# ── Session transfer-area management ─────────────────────────────────────────

# session_id → {"tmpdir": str, "known": set[str]}
_sessions: dict[str, dict] = {}
_sessions_lock = threading.Lock()


def _create_session(session_id: str) -> str:
    """Create a temp directory for this session and start a file-watcher thread."""
    tmpdir = tempfile.mkdtemp(prefix=f"acp-{session_id[:8]}-")
    with _sessions_lock:
        _sessions[session_id] = {"tmpdir": tmpdir, "known": set()}
    threading.Thread(
        target=_watch_session, args=(session_id,), daemon=True
    ).start()
    return tmpdir


def _watch_session(session_id: str):
    """Poll the session transfer area; broadcast file_created for new files."""
    while _bridge and _bridge.alive:
        with _sessions_lock:
            info = _sessions.get(session_id)
        if info is None:
            break
        tmpdir = info["tmpdir"]
        known  = info["known"]
        try:
            current = set(os.listdir(tmpdir))
        except OSError:
            break
        for fname in current - known:
            known.add(fname)
            try:
                size = os.path.getsize(os.path.join(tmpdir, fname))
            except OSError:
                size = 0
            if _bridge:
                _bridge._broadcast("file_created", {
                    "sessionId": session_id,
                    "filename":  fname,
                    "size":      size,
                })
        time.sleep(1)


def _cleanup_sessions():
    with _sessions_lock:
        for info in _sessions.values():
            tmpdir = info.get("tmpdir", "")
            if tmpdir and os.path.isdir(tmpdir):
                shutil.rmtree(tmpdir, ignore_errors=True)
        _sessions.clear()


atexit.register(_cleanup_sessions)


# ── GooseBridge ───────────────────────────────────────────────────────────────

class GooseBridge:
    """Manages the goose ACP subprocess; routes JSON-RPC between the process and HTTP clients."""

    def __init__(self, cmd: list[str]):
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._req_id = 0
        self._lock   = threading.Lock()
        self._response_queues: dict[int, queue.Queue] = {}

        # Fan-out: each connected SSE client gets its own copy of events
        self._subscribers: list[queue.Queue] = []
        self._sub_lock = threading.Lock()

        threading.Thread(target=self._read_loop,   daemon=True).start()
        threading.Thread(target=self._stderr_loop, daemon=True).start()

    # ── I/O threads ──────────────────────────────────────────────────────────

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
                self._broadcast("notification", msg)
            elif has_method and msg_id is not None:
                self._broadcast("server_request", msg)
            elif msg_id is not None:
                with self._lock:
                    q = self._response_queues.get(msg_id)
                if q:
                    q.put(msg)

    def _stderr_loop(self):
        for line in self._proc.stderr:
            line = line.rstrip()
            if line:
                print(f"[goose] {line}", file=sys.stderr, flush=True)

    # ── SSE fan-out ──────────────────────────────────────────────────────────

    def _broadcast(self, event_type: str, msg: dict):
        with self._sub_lock:
            for q in self._subscribers:
                q.put((event_type, msg))

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue()
        with self._sub_lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue):
        with self._sub_lock:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass

    # ── Request / Response ────────────────────────────────────────────────────

    def send_request(self, method: str, params: Optional[dict], timeout: float = 300.0) -> dict:
        with self._lock:
            self._req_id += 1
            req_id = self._req_id
            q: queue.Queue = queue.Queue()
            self._response_queues[req_id] = q

        payload: dict = {"jsonrpc": "2.0", "method": method, "id": req_id}
        if params:
            payload["params"] = params

        self._proc.stdin.write(json.dumps(payload) + "\n")
        self._proc.stdin.flush()

        try:
            return q.get(timeout=timeout)
        except queue.Empty:
            return {"error": {"code": -32000, "message": "Timed out waiting for goose"}}
        finally:
            with self._lock:
                self._response_queues.pop(req_id, None)

    def write_raw(self, msg: dict):
        self._proc.stdin.write(json.dumps(msg) + "\n")
        self._proc.stdin.flush()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @property
    def alive(self) -> bool:
        return self._proc.poll() is None

    def close(self):
        try:
            self._proc.terminate()
            self._proc.wait(timeout=5)
        except Exception:
            pass


# ── Flask app ─────────────────────────────────────────────────────────────────

app = Flask(__name__)
_bridge: Optional[GooseBridge] = None
_goose_cmd: list[str] = []


# ── Core endpoints ────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    ok = bool(_bridge and _bridge.alive)
    return jsonify({"status": "ok" if ok else "down"}), (200 if ok else 503)


@app.get("/info")
def info():
    provider, model = _goose_config()
    return jsonify({
        "provider": provider,
        "model":    model,
        "cmd":      " ".join(_goose_cmd),
        "alive":    bool(_bridge and _bridge.alive),
    })


@app.get("/events")
def events():
    if not _bridge:
        return jsonify({"error": "bridge not ready"}), 503

    sub_q = _bridge.subscribe()

    def generate():
        try:
            while _bridge and _bridge.alive:
                try:
                    event_type, data = sub_q.get(timeout=15)
                    yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            _bridge.unsubscribe(sub_q)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/rpc")
def rpc():
    if not _bridge or not _bridge.alive:
        return jsonify({"error": {"code": -32000, "message": "goose not running"}}), 503

    body    = flask_request.get_json(force=True, silent=True) or {}
    method  = body.get("method", "")
    params  = body.get("params") or None
    timeout = float(flask_request.args.get("timeout", 300))

    if not method:
        return jsonify({"error": {"code": -32600, "message": "Missing method"}}), 400

    result = _bridge.send_request(method, params, timeout=timeout)

    # On successful session/new, create a transient transfer area for the session
    if method == "session/new" and "result" in result:
        sid = result["result"].get("sessionId")
        if sid and sid not in _sessions:
            transfer_dir = _create_session(sid)
            result["result"]["transferDir"] = transfer_dir

    return jsonify(result)


@app.post("/reply")
def reply():
    if not _bridge:
        return jsonify({"error": "bridge not ready"}), 503
    body = flask_request.get_json(force=True, silent=True) or {}
    _bridge.write_raw(body)
    return jsonify({"ok": True})


@app.post("/notify")
def notify():
    if not _bridge:
        return jsonify({"error": "bridge not ready"}), 503
    body = flask_request.get_json(force=True, silent=True) or {}
    _bridge.write_raw(body)
    return jsonify({"ok": True})


# ── File transfer endpoints ───────────────────────────────────────────────────

@app.post("/files/<session_id>")
def upload_file(session_id):
    """Upload a file into the session transfer area.

    The watcher tracks which files were uploaded so it does NOT re-emit a
    file_created event for them — only files written by goose trigger that.
    """
    with _sessions_lock:
        info = _sessions.get(session_id)
    if info is None:
        return jsonify({"error": "unknown session"}), 404

    uploaded = flask_request.files.get("file")
    if not uploaded:
        return jsonify({"error": "no file in request"}), 400

    filename = secure_filename(uploaded.filename or "upload")
    if not filename:
        return jsonify({"error": "invalid filename"}), 400

    dest = os.path.join(info["tmpdir"], filename)
    uploaded.save(dest)
    # Mark as known so the watcher ignores it
    info["known"].add(filename)

    return jsonify({
        "filename": filename,
        "path":     dest,
        "size":     os.path.getsize(dest),
    })


@app.get("/files/<session_id>")
def list_files(session_id):
    """List files currently in the session transfer area."""
    with _sessions_lock:
        info = _sessions.get(session_id)
    if info is None:
        return jsonify({"error": "unknown session"}), 404

    tmpdir = info["tmpdir"]
    files  = []
    try:
        for name in sorted(os.listdir(tmpdir)):
            fpath = os.path.join(tmpdir, name)
            if os.path.isfile(fpath):
                files.append({"name": name, "size": os.path.getsize(fpath)})
    except OSError:
        pass

    return jsonify({"files": files, "dir": tmpdir})


@app.get("/files/<session_id>/<path:filename>")
def download_file(session_id, filename):
    """Download a file from the session transfer area."""
    with _sessions_lock:
        info = _sessions.get(session_id)
    if info is None:
        return jsonify({"error": "unknown session"}), 404

    # Guard against path traversal
    safe = secure_filename(filename)
    fpath = os.path.join(info["tmpdir"], safe)
    if not os.path.isfile(fpath):
        return jsonify({"error": "file not found"}), 404

    return send_file(fpath, as_attachment=True, download_name=safe)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    global _bridge, _goose_cmd

    parser = argparse.ArgumentParser(
        description="Goose ACP HTTP+SSE bridge — exposes 'goose acp' over HTTP.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 acp-server.py
  python3 acp-server.py --builtin developer,memory --port 7464
  python3 acp-server.py --host 0.0.0.0 --port 7464
        """,
    )
    parser.add_argument("--builtin", "-b", default="developer",
                        metavar="NAME[,NAME…]",
                        help="Comma-separated builtin extensions (default: developer)")
    parser.add_argument("--goose", default="goose", metavar="CMD",
                        help="Path/name of the goose executable (default: goose)")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Bind address (default: 127.0.0.1; use 0.0.0.0 for all interfaces)")
    parser.add_argument("--port", "-p", type=int, default=7464,
                        help="Listen port (default: 7464)")
    args = parser.parse_args()

    _goose_cmd = [args.goose, "acp"]
    if args.builtin:
        _goose_cmd += ["--with-builtin", args.builtin]

    provider, model = _goose_config()
    w = 46
    print()
    print("  Goose ACP HTTP+SSE Server")
    print("  " + "─" * w)
    print(f"  Command  : {' '.join(_goose_cmd)}")
    print(f"  Provider : {provider}")
    print(f"  Model    : {model}")
    print(f"  Listening: http://{args.host}:{args.port}")
    print("  " + "─" * w)
    print()

    _bridge = GooseBridge(_goose_cmd)

    try:
        app.run(host=args.host, port=args.port, threaded=True, use_reloader=False)
    finally:
        _bridge.close()


if __name__ == "__main__":
    main()
