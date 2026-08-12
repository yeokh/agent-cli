#!/usr/bin/env python3
"""
Interactive chat program for the Goose ACP (Agent Client Protocol) server.

Spawns 'goose acp' as a subprocess and communicates via JSON-RPC 2.0 over stdio.
"""

import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

# ── ANSI colours ──────────────────────────────────────────────────────────────
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
CYAN    = "\033[96m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
MAGENTA = "\033[95m"
RED     = "\033[91m"
BLUE    = "\033[94m"
GRAY    = "\033[90m"

def _c(colour: str, text: str) -> str:
    return f"{colour}{text}{RESET}"


# ── ACP Client ────────────────────────────────────────────────────────────────

class AcpClient:
    """JSON-RPC 2.0 client that talks to a 'goose acp' subprocess over stdio."""

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
        self._lock = threading.Lock()

        # Pending response queues keyed by request id
        self._response_queues: dict[int, queue.Queue] = {}

        # Server-initiated requests (e.g. requestPermission) — main thread drains these
        self.server_requests: queue.Queue = queue.Queue()

        # Streaming notifications — main thread drains these
        self.notifications: queue.Queue = queue.Queue()

        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

        self._stderr_reader = threading.Thread(target=self._stderr_loop, daemon=True)
        self._stderr_reader.start()

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

            msg_id  = msg.get("id")
            has_method = "method" in msg

            if has_method and msg_id is None:
                # Pure notification (no id) — stream update
                self.notifications.put(msg)
            elif has_method and msg_id is not None:
                # Server-initiated request (e.g. session/request_permission) — main thread handles
                self.server_requests.put(msg)
            elif msg_id is not None:
                # Response to one of our requests
                with self._lock:
                    q = self._response_queues.get(msg_id)
                if q:
                    q.put(msg)

    def _stderr_loop(self):
        for line in self._proc.stderr:
            line = line.rstrip()
            if line:
                print(_c(GRAY, f"  [goose] {line}"), file=sys.stderr, flush=True)

    # ── Request / Response ────────────────────────────────────────────────────

    def request(
        self,
        method: str,
        params: Optional[dict] = None,
        timeout: float = 60.0,
        on_notification=None,
        on_server_request=None,
    ) -> dict:
        """Send a JSON-RPC request and wait for the matching response.

        While waiting, drains notifications and server requests (e.g. permission
        prompts) by calling the provided callbacks so the MAIN thread handles them.
        """
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
                    return {"error": {"code": -32000, "message": "Timed out waiting for response"}}

                # Drain any pending notifications / server-requests before blocking
                self._drain(on_notification, on_server_request)

                try:
                    return q.get(timeout=min(remaining, 0.05))
                except queue.Empty:
                    continue
        finally:
            with self._lock:
                self._response_queues.pop(req_id, None)

    def _drain(self, on_notification=None, on_server_request=None):
        """Process all currently queued notifications and server requests."""
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
        """Send a response to a server-initiated request."""
        msg = {"jsonrpc": "2.0", "id": req_id, "result": result}
        self._proc.stdin.write(json.dumps(msg) + "\n")
        self._proc.stdin.flush()

    def notify(self, method: str, params: Optional[dict] = None):
        """Send a JSON-RPC notification (no response expected)."""
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


# ── Notification / permission rendering ──────────────────────────────────────

class StreamRenderer:
    """Renders ACP streaming notifications and permission requests to the terminal.
    All methods are called from the MAIN thread only.
    """

    def __init__(self, client: AcpClient):
        self._client = client
        self._active_tools: dict[str, str] = {}
        self._in_response = False

    # ── callbacks passed to client.request() ─────────────────────────────────

    def on_notification(self, msg: dict):
        method = msg.get("method", "")
        if method == "session/update":
            self._handle_session_update(msg)

    def on_server_request(self, msg: dict):
        method = msg.get("method", "")
        # goose 1.39: "session/request_permission"; ACP spec: "requestPermission"
        if method in ("session/request_permission", "requestPermission"):
            self._handle_permission_request(msg)

    # ── internals ─────────────────────────────────────────────────────────────

    def _handle_session_update(self, msg: dict):
        """Handle session/update notifications (goose 1.39 format)."""
        update = msg.get("params", {}).get("update", {})
        kind   = update.get("sessionUpdate", "")

        if kind == "agent_message_chunk":
            content = update.get("content", {})
            text    = content.get("text", "") if isinstance(content, dict) else str(content)
            if text:
                if not self._in_response:
                    print(_c(CYAN, "\nGoose: "), end="", flush=True)
                    self._in_response = True
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

        # Ignore: session_info_update, usage_update, etc.

    def _handle_permission_request(self, msg: dict):
        """Handle session/request_permission — always called from main thread."""
        req_id  = msg.get("id")
        params  = msg.get("params", {})
        # goose 1.39 uses params.toolCall; ACP spec uses params.toolCallUpdate.fields
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

        # Default to option 1 (usually allow_always or allow_once)
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
        """Flush any queued notifications/server-requests (e.g. before showing prompt)."""
        self._client._drain(self.on_notification, self.on_server_request)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_error(resp: dict) -> str:
    err = resp.get("error", {})
    return err.get("message", str(err))


def _goose_config() -> tuple[str, str]:
    """Return (provider, model) from ~/.config/goose/config.yaml, or ('?', '?')."""
    cfg_path = Path.home() / ".config" / "goose" / "config.yaml"
    try:
        text = cfg_path.read_text()
        # Minimal YAML key extraction — avoids a pyyaml dependency
        provider = "?"
        model    = "?"
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("active_provider:"):
                provider = line.split(":", 1)[1].strip()
            elif line.startswith("model:"):
                model = line.split(":", 1)[1].strip()
        return provider, model
    except Exception:
        return "?", "?"


def _banner(session_id: str, cwd: str):
    provider, model = _goose_config()
    w = 46
    print()
    print(_c(BOLD + CYAN,  "  Goose ACP Chat"))
    print(_c(DIM,          "  " + "─" * w))
    print(_c(DIM,          f"  Session  : {session_id[:8]}…"))
    print(_c(DIM,          f"  Provider : {provider}"))
    print(_c(DIM,          f"  Model    : {model}"))
    print(_c(DIM,          f"  CWD      : {cwd}"))
    print(_c(DIM,          "  " + "─" * w))
    print(_c(DIM,          "  Type your message and press Enter."))
    print(_c(DIM,          "  Commands: /quit  /session  /cancel"))
    print(_c(DIM,          "  " + "─" * w))
    print()


# ── Chat session ──────────────────────────────────────────────────────────────

def run_chat(cmd: list[str], cwd: str) -> int:
    print(_c(BOLD, "\nStarting goose acp…"), flush=True)

    client   = AcpClient(cmd)
    renderer = StreamRenderer(client)

    cbs = dict(on_notification=renderer.on_notification,
               on_server_request=renderer.on_server_request)

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

    result     = resp.get("result", {})
    session_id = result.get("sessionId", "unknown")

    # Drain any messages that arrived during or just after session creation
    renderer.drain_pending()

    _banner(session_id, cwd)

    # ── chat loop ─────────────────────────────────────────────────────────────
    try:
        while client.alive:
            # Drain any late-arriving messages before prompting
            renderer.drain_pending()

            try:
                user_input = input(_c(BOLD + BLUE, "You: ")).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not user_input:
                continue

            if user_input.lower() in ("/quit", "/exit", "/q"):
                break

            if user_input.lower() == "/session":
                print(_c(DIM, f"  Session ID: {session_id}"))
                continue

            if user_input.lower() == "/cancel":
                client.notify("session/cancel", {"sessionId": session_id})
                print(_c(YELLOW, "  Cancel sent."))
                continue

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

    print(_c(DIM, "\nClosing session…"))
    client.close()
    print(_c(BOLD, "Goodbye!"))
    return 0


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Interactive chat client for the Goose ACP server.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 acp-chat.py
  python3 acp-chat.py --builtin developer
  python3 acp-chat.py --builtin developer,memory --cwd /my/project
        """,
    )
    parser.add_argument(
        "--builtin", "-b",
        default="developer",
        metavar="NAME[,NAME…]",
        help="Comma-separated builtin extensions to enable (default: developer)",
    )
    parser.add_argument(
        "--cwd", "-C",
        default=os.getcwd(),
        metavar="PATH",
        help="Working directory reported to the agent (default: current directory)",
    )
    parser.add_argument(
        "--goose",
        default="goose",
        metavar="CMD",
        help="Path/name of the goose executable (default: goose)",
    )
    args = parser.parse_args()

    cmd = [args.goose, "acp"]
    if args.builtin:
        cmd += ["--with-builtin", args.builtin]

    sys.exit(run_chat(cmd, cwd=args.cwd))


if __name__ == "__main__":
    main()
