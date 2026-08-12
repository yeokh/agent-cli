#!/usr/bin/env python3
"""
Interactive chat client for the Goose ACP HTTP+SSE server.

Connects to an acp-server.py instance over HTTP.
Notifications and server-initiated requests arrive via SSE (GET /events).
Requests go via POST /rpc; permission replies via POST /reply.
Files are exchanged through the session transfer area managed by the server.

Usage:
  python3 acp-client.py
  python3 acp-client.py --server http://localhost:7464
  python3 acp-client.py --server http://remote-host:7464 --cwd /my/project
"""

import argparse
import json
import os
import queue
import sys
import threading
import time
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    sys.exit("requests is required:  pip install requests")

# ── ANSI colours ──────────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BLUE   = "\033[94m"
GRAY   = "\033[90m"

def _c(colour: str, text: str) -> str:
    return f"{colour}{text}{RESET}"

def _fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


# ── AcpClient ─────────────────────────────────────────────────────────────────

class AcpClient:
    """JSON-RPC 2.0 client over HTTP+SSE (connects to acp-server.py)."""

    def __init__(self, base_url: str):
        self._base    = base_url.rstrip("/")
        self._http    = requests.Session()
        self._running = True

        # Queues populated by the SSE background thread
        self.notifications:   queue.Queue = queue.Queue()
        self.server_requests: queue.Queue = queue.Queue()
        self.file_events:     queue.Queue = queue.Queue()

        self._sse_thread = threading.Thread(target=self._sse_loop, daemon=True)
        self._sse_thread.start()

    # ── SSE thread ───────────────────────────────────────────────────────────

    def _sse_loop(self):
        """Subscribe to GET /events and populate queues from SSE events.

        Each SSE event is two lines: `event: TYPE` then `data: JSON`.
        requests.iter_lines() strips blank lines, so we dispatch as soon as
        we see a `data:` line, using the most-recently-seen `event:` value.
        """
        while self._running:
            try:
                resp = self._http.get(
                    f"{self._base}/events",
                    stream=True,
                    headers={"Accept": "text/event-stream"},
                    timeout=(10, None),   # (connect_timeout, read_timeout=infinite)
                )
                resp.raise_for_status()

                event_type: Optional[str] = None
                for line in resp.iter_lines(decode_unicode=True):
                    if not self._running:
                        break
                    if line.startswith("event:"):
                        event_type = line[len("event:"):].strip()
                    elif line.startswith("data:"):
                        data_str = line[len("data:"):].strip()
                        try:
                            msg = json.loads(data_str)
                        except json.JSONDecodeError:
                            event_type = None
                            continue
                        if event_type == "notification":
                            self.notifications.put(msg)
                        elif event_type == "server_request":
                            self.server_requests.put(msg)
                        elif event_type == "file_created":
                            self.file_events.put(msg)
                        event_type = None
                    # comment lines (": keepalive") are silently ignored

            except Exception as exc:
                if self._running:
                    print(_c(GRAY, f"  [sse] reconnecting ({exc})"), file=sys.stderr)
                    time.sleep(2)

    # ── Request / Response ────────────────────────────────────────────────────

    def request(
        self,
        method: str,
        params: Optional[dict] = None,
        timeout: float = 300.0,
        on_notification=None,
        on_server_request=None,
        on_file_created=None,
    ) -> dict:
        """POST /rpc and wait for the response, draining SSE queues while blocking.

        The HTTP POST runs in a daemon thread so the main thread can continue
        calling _drain() to handle streaming notifications and permission prompts.
        """
        body: dict = {"jsonrpc": "2.0", "method": method}
        if params:
            body["params"] = params

        result_q: queue.Queue = queue.Queue()

        def do_post():
            try:
                r = self._http.post(
                    f"{self._base}/rpc",
                    json=body,
                    params={"timeout": timeout},
                    timeout=timeout + 10,
                )
                result_q.put(r.json())
            except Exception as exc:
                result_q.put({"error": {"code": -32000, "message": str(exc)}})

        threading.Thread(target=do_post, daemon=True).start()

        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return {"error": {"code": -32000, "message": "Timed out"}}

            self._drain(on_notification, on_server_request, on_file_created)

            try:
                return result_q.get(timeout=min(remaining, 0.05))
            except queue.Empty:
                continue

    def _drain(self, on_notification=None, on_server_request=None, on_file_created=None):
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
        while True:
            try:
                msg = self.file_events.get_nowait()
                if on_file_created:
                    on_file_created(msg)
            except queue.Empty:
                break

    def reply(self, req_id: int, result: dict):
        """POST /reply to send a response to a server-initiated request."""
        msg = {"jsonrpc": "2.0", "id": req_id, "result": result}
        try:
            self._http.post(f"{self._base}/reply", json=msg, timeout=10)
        except Exception:
            pass

    def notify(self, method: str, params: Optional[dict] = None):
        """POST /notify to send a JSON-RPC notification (no response expected)."""
        msg: dict = {"jsonrpc": "2.0", "method": method}
        if params:
            msg["params"] = params
        try:
            self._http.post(f"{self._base}/notify", json=msg, timeout=10)
        except Exception:
            pass

    @property
    def alive(self) -> bool:
        try:
            r = self._http.get(f"{self._base}/health", timeout=3)
            return r.ok and r.json().get("status") == "ok"
        except Exception:
            return False

    def close(self):
        self._running = False
        self._http.close()


# ── StreamRenderer ────────────────────────────────────────────────────────────

class StreamRenderer:
    """Renders ACP streaming notifications and permission requests to the terminal.
    Also handles file_created events by auto-downloading new server output files.
    All methods are called from the MAIN thread only.
    """

    def __init__(self, client: AcpClient, server_url: str, downloads_dir: str):
        self._client       = client
        self._server_url   = server_url
        self._downloads_dir = downloads_dir
        self._active_tools: dict[str, str] = {}
        self._in_response  = False
        self._response_buf: list[str] = []   # accumulates text for /save
        self._session_id: Optional[str] = None

    def set_session(self, session_id: str):
        self._session_id = session_id

    def get_last_response(self) -> str:
        return "".join(self._response_buf)

    # ── callbacks passed to client.request() ─────────────────────────────────

    def on_notification(self, msg: dict):
        if msg.get("method") == "session/update":
            self._handle_session_update(msg)

    def on_server_request(self, msg: dict):
        if msg.get("method") in ("session/request_permission", "requestPermission"):
            self._handle_permission_request(msg)

    def on_file_created(self, msg: dict):
        """Auto-download a file that goose wrote to the session transfer area."""
        filename   = msg.get("filename", "")
        size       = msg.get("size", 0)
        session_id = msg.get("sessionId") or self._session_id
        if not filename or not session_id:
            return

        self._flush_response()
        print(_c(GREEN, f"\n  [file] {filename} ({_fmt_size(size)}) — downloading…"), flush=True)

        local_path = Path(self._downloads_dir) / filename
        try:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            r = self._client._http.get(
                f"{self._server_url}/files/{session_id}/{filename}",
                stream=True,
                timeout=(10, 120),
            )
            if r.ok:
                with open(local_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(_c(GREEN, f"  [file] saved → {local_path}"), flush=True)
            else:
                print(_c(RED, f"  [file] download failed ({r.status_code})"), flush=True)
        except Exception as exc:
            print(_c(RED, f"  [file] download error: {exc}"), flush=True)

    # ── internals ─────────────────────────────────────────────────────────────

    def _handle_session_update(self, msg: dict):
        update = msg.get("params", {}).get("update", {})
        kind   = update.get("sessionUpdate", "")

        if kind == "agent_message_chunk":
            content = update.get("content", {})
            text    = content.get("text", "") if isinstance(content, dict) else str(content)
            if text:
                if not self._in_response:
                    print(_c(CYAN, "\nGoose: "), end="", flush=True)
                    self._in_response = True
                self._response_buf.append(text)
                print(text, end="", flush=True)

        elif kind == "tool_call":
            tc_id = update.get("toolCallId", "")
            title = update.get("title", "tool")
            self._active_tools[tc_id] = title
            self._flush_response()
            print(_c(YELLOW, f"  [tool] {title}"), flush=True)

        elif kind == "tool_call_update":
            tc_id  = update.get("toolCallId", "")
            status = update.get("status", "")
            title  = self._active_tools.get(tc_id, "tool")
            if status == "success":
                print(_c(GREEN, f"  [done] {title}"), flush=True)
            elif status == "failed":
                print(_c(RED,   f"  [fail] {title}"), flush=True)

    def _handle_permission_request(self, msg: dict):
        req_id  = msg.get("id")
        params  = msg.get("params", {})
        tc      = params.get("toolCall", params.get("toolCallUpdate", {}).get("fields", {}))
        title   = tc.get("title", "Unknown operation")
        raw_in  = tc.get("rawInput", {})
        options = params.get("options", [])

        self._flush_response()
        print()
        print(_c(BOLD + YELLOW, "  Permission required:"), _c(BOLD, title))
        if raw_in:
            raw_str = json.dumps(raw_in) if isinstance(raw_in, dict) else str(raw_in)
            print(_c(DIM, f"  Input: {raw_str[:200]}"))
        print(_c(YELLOW, "  Options:"))
        for i, opt in enumerate(options, 1):
            print(f"    {i}. {opt.get('name', opt.get('optionId', '?'))}")

        chosen_id = options[0].get("optionId", "allow_once") if options else "allow_once"
        while True:
            try:
                choice = input(_c(YELLOW, "  Choose [1]: ")).strip() or "1"
            except (EOFError, KeyboardInterrupt):
                break
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(options):
                    chosen_id = options[idx].get("optionId", "allow_once")
                    break
            except ValueError:
                pass
            print(_c(RED, "  Invalid choice, try again."))

        if req_id is not None:
            self._client.reply(req_id, {"outcome": {"type": "selected", "optionId": chosen_id}})

    def _flush_response(self):
        if self._in_response:
            print(flush=True)
            self._in_response = False

    def end_turn(self):
        self._flush_response()
        self._active_tools.clear()

    def drain_pending(self):
        """Flush any queued notifications/server-requests/file-events."""
        self._client._drain(
            self.on_notification,
            self.on_server_request,
            self.on_file_created,
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_error(resp: dict) -> str:
    err = resp.get("error", {})
    return err.get("message", str(err)) if isinstance(err, dict) else str(err)


def _banner(server_url: str, session_id: str, cwd: str, transfer_dir: str, info: dict):
    w = 50
    print()
    print(_c(BOLD + CYAN, "  Goose ACP Chat"))
    print(_c(DIM,         "  " + "─" * w))
    print(_c(DIM,         f"  Server   : {server_url}"))
    print(_c(DIM,         f"  Session  : {session_id[:8]}…"))
    print(_c(DIM,         f"  Provider : {info.get('provider', '?')}"))
    print(_c(DIM,         f"  Model    : {info.get('model', '?')}"))
    print(_c(DIM,         f"  CWD      : {cwd}"))
    if transfer_dir:
        print(_c(DIM,     f"  Transfer : {transfer_dir}"))
    print(_c(DIM,         "  " + "─" * w))
    print(_c(DIM,         "  Type your message and press Enter."))
    print(_c(DIM,         "  /quit  /session  /cancel  /ls  /rls  /attach  /download  /save"))
    print(_c(DIM,         "  " + "─" * w))
    print()


def _cmd_ls(path_str: str):
    """List local directory contents."""
    target = Path(path_str or ".").expanduser()
    try:
        entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        if not entries:
            print(_c(DIM, f"  (empty) {target}"))
            return
        print(_c(DIM, f"  {target}/"))
        for e in entries:
            if e.is_dir():
                print(_c(BLUE, f"    {e.name}/"))
            else:
                print(f"    {e.name}  {_c(DIM, _fmt_size(e.stat().st_size))}")
    except Exception as exc:
        print(_c(RED, f"  {exc}"))


# ── Chat session ──────────────────────────────────────────────────────────────

def run_chat(server_url: str, cwd: str, downloads_dir: str) -> int:
    print(_c(BOLD, f"\nConnecting to {server_url}…"), flush=True)

    client   = AcpClient(server_url)
    renderer = StreamRenderer(client, server_url, downloads_dir)

    cbs = dict(
        on_notification=renderer.on_notification,
        on_server_request=renderer.on_server_request,
        on_file_created=renderer.on_file_created,
    )

    time.sleep(0.3)   # allow SSE connection to establish

    if not client.alive:
        print(_c(RED, "Server is not reachable. Is acp-server.py running?"))
        client.close()
        return 1

    # ── initialize ───────────────────────────────────────────────────────────
    resp = client.request("initialize", {
        "protocolVersion": "v1",
        "clientCapabilities": {},
        "clientInfo": {"name": "goose-chat-py", "version": "1.0.0"},
    }, **cbs)
    if "error" in resp:
        print(_c(RED, f"Initialize failed: {_extract_error(resp)}"))
        client.close()
        return 1

    result     = resp.get("result", {})
    agent_info = result.get("agentInfo", {})
    caps       = result.get("agentCapabilities", {})
    agent_name = agent_info.get("name", "goose")
    agent_ver  = agent_info.get("version", "?")
    print(_c(GREEN, f"  Connected to {agent_name} {agent_ver}"))
    pc = caps.get("promptCapabilities", {})
    print(_c(DIM, f"  Capabilities: image={pc.get('image', False)}, "
                   f"audio={pc.get('audio', False)}"))

    # ── session/new ──────────────────────────────────────────────────────────
    resp = client.request("session/new", {"cwd": cwd, "mcpServers": []}, **cbs)
    if "error" in resp:
        print(_c(RED, f"Session creation failed: {_extract_error(resp)}"))
        client.close()
        return 1

    result       = resp.get("result", {})
    session_id   = result.get("sessionId", "unknown")
    transfer_dir = result.get("transferDir", "")   # injected by server

    renderer.set_session(session_id)

    # ── banner ───────────────────────────────────────────────────────────────
    try:
        server_info = requests.get(f"{server_url}/info", timeout=3).json()
    except Exception:
        server_info = {}

    renderer.drain_pending()
    _banner(server_url, session_id, cwd, transfer_dir, server_info)

    # ── chat loop ─────────────────────────────────────────────────────────────
    try:
        while client.alive:
            renderer.drain_pending()

            try:
                user_input = input(_c(BOLD + BLUE, "You: ")).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not user_input:
                continue

            # ── built-in commands ─────────────────────────────────────────────

            if user_input.lower() in ("/quit", "/exit", "/q"):
                break

            if user_input.lower() == "/session":
                print(_c(DIM, f"  Session ID   : {session_id}"))
                print(_c(DIM, f"  Transfer area: {transfer_dir or '(none)'}"))
                continue

            if user_input.lower() == "/cancel":
                client.notify("session/cancel", {"sessionId": session_id})
                print(_c(YELLOW, "  Cancel sent."))
                continue

            # /ls [local-dir]
            if user_input.lower().startswith("/ls"):
                parts = user_input.split(maxsplit=1)
                _cmd_ls(parts[1] if len(parts) > 1 else ".")
                continue

            # /rls — list server transfer area
            if user_input.lower() == "/rls":
                if not transfer_dir:
                    print(_c(YELLOW, "  No transfer area (session not ready)."))
                    continue
                try:
                    r = requests.get(f"{server_url}/files/{session_id}", timeout=5)
                    data  = r.json()
                    files = data.get("files", [])
                    print(_c(DIM, f"  Transfer area: {data.get('dir', transfer_dir)}"))
                    if files:
                        for f in files:
                            print(f"    {f['name']}  {_c(DIM, _fmt_size(f['size']))}")
                    else:
                        print(_c(DIM, "  (empty)"))
                except Exception as exc:
                    print(_c(RED, f"  {exc}"))
                continue

            # /attach <local-path> [message]
            if user_input.lower().startswith("/attach "):
                parts      = user_input.split(maxsplit=2)
                local_path = parts[1] if len(parts) > 1 else ""
                extra_msg  = parts[2] if len(parts) > 2 else ""

                if not local_path:
                    print(_c(RED, "  Usage: /attach <local-file> [message]"))
                    continue
                if not transfer_dir:
                    print(_c(RED, "  No transfer area — session not ready."))
                    continue

                local_file = Path(local_path).expanduser()
                if not local_file.is_file():
                    print(_c(RED, f"  File not found: {local_path}"))
                    continue

                print(_c(DIM, f"  Uploading {local_file.name}…"), flush=True)
                try:
                    with open(local_file, "rb") as fh:
                        r = requests.post(
                            f"{server_url}/files/{session_id}",
                            files={"file": (local_file.name, fh)},
                            timeout=60,
                        )
                    if not r.ok:
                        print(_c(RED, f"  Upload failed: {r.text}"))
                        continue
                    info      = r.json()
                    srv_path  = info.get("path", "")
                    fname     = info.get("filename", local_file.name)
                    size      = info.get("size", 0)
                    print(_c(GREEN, f"  Uploaded: {fname} ({_fmt_size(size)}) → {srv_path}"))
                except Exception as exc:
                    print(_c(RED, f"  Upload error: {exc}"))
                    continue

                # Build the prompt to send to goose
                default_msg = f"Please process the file '{fname}'."
                user_input  = (
                    f"File '{fname}' has been placed at {srv_path}. "
                    f"{extra_msg or default_msg}"
                )
                # fall through to send the prompt below

            # /download <filename> [local-path]
            elif user_input.lower().startswith("/download "):
                parts       = user_input.split(maxsplit=2)
                remote_name = parts[1] if len(parts) > 1 else ""
                local_dest  = parts[2] if len(parts) > 2 else remote_name

                if not remote_name:
                    print(_c(RED, "  Usage: /download <filename> [local-path]"))
                    continue
                if not session_id:
                    print(_c(RED, "  No active session."))
                    continue

                try:
                    r = requests.get(
                        f"{server_url}/files/{session_id}/{remote_name}",
                        stream=True,
                        timeout=(10, 120),
                    )
                    if not r.ok:
                        print(_c(RED, f"  Download failed ({r.status_code}): {r.text}"))
                        continue
                    Path(local_dest).parent.mkdir(parents=True, exist_ok=True)
                    with open(local_dest, "wb") as fh:
                        for chunk in r.iter_content(chunk_size=8192):
                            fh.write(chunk)
                    size = Path(local_dest).stat().st_size
                    print(_c(GREEN, f"  Downloaded: {remote_name} → {local_dest} ({_fmt_size(size)})"))
                except Exception as exc:
                    print(_c(RED, f"  Download error: {exc}"))
                continue

            # /save [local-path]
            elif user_input.lower().startswith("/save"):
                parts      = user_input.split(maxsplit=1)
                local_dest = parts[1].strip() if len(parts) > 1 else f"response_{int(time.time())}.txt"
                text       = renderer.get_last_response()

                if not text:
                    print(_c(YELLOW, "  No agent response to save yet."))
                    continue
                try:
                    Path(local_dest).parent.mkdir(parents=True, exist_ok=True)
                    Path(local_dest).write_text(text, encoding="utf-8")
                    print(_c(GREEN, f"  Saved {len(text)} chars → {local_dest}"))
                except Exception as exc:
                    print(_c(RED, f"  Save failed: {exc}"))
                continue

            # ── send prompt to goose ───────────────────────────────────────────
            renderer._response_buf.clear()   # reset for this turn

            resp = client.request("session/prompt", {
                "sessionId": session_id,
                "prompt": [{"type": "text", "text": user_input}],
            }, timeout=300.0, **cbs)

            renderer.end_turn()

            if "error" in resp:
                print(_c(RED, f"\nError: {_extract_error(resp)}"))
            else:
                stop = resp.get("result", {}).get("stopReason", "")
                if stop and stop != "endTurn":
                    print(_c(DIM, f"  [{stop}]"))

            print()

    except KeyboardInterrupt:
        print()

    print(_c(DIM, "\nDisconnecting…"))
    client.close()
    print(_c(BOLD, "Goodbye!"))
    return 0


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Interactive chat client for the Goose ACP HTTP+SSE server.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 acp-client.py
  python3 acp-client.py --server http://localhost:7464
  python3 acp-client.py --server http://remote-host:7464 --cwd /my/project

File commands (in chat):
  /attach <local-file> [msg]   upload a file to the server transfer area
  /download <name> [local]     download a file from the server transfer area
  /rls                         list files in the server transfer area
  /ls [dir]                    list local directory
  /save [file]                 save the last agent response to a local file
        """,
    )
    parser.add_argument(
        "--server", "-s",
        default="http://127.0.0.1:7464",
        metavar="URL",
        help="ACP server URL (default: http://127.0.0.1:7464)",
    )
    parser.add_argument(
        "--cwd", "-C",
        default=os.getcwd(),
        metavar="PATH",
        help="Working directory reported to the agent (default: current directory)",
    )
    parser.add_argument(
        "--downloads", "-d",
        default=".",
        metavar="DIR",
        help="Local directory for auto-downloaded server output files (default: .)",
    )
    args = parser.parse_args()

    sys.exit(run_chat(args.server, cwd=args.cwd, downloads_dir=args.downloads))


if __name__ == "__main__":
    main()
