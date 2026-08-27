#!/usr/bin/env python3
"""
Interactive chat client for the Hermes A2A gateway.

Sends messages via message/stream (SSE) for live streaming output.
Maintains a contextId across turns for multi-turn conversation.

Usage:
  python3 a2a_chat.py
  python3 a2a_chat.py --server http://localhost:9900
"""

import argparse
import json
import sys
import time
from typing import Optional

# Hermes anti-loop limit: gateway rejects contexts after this many turns.
# Rotate to a fresh context automatically just before the wall is hit.
CONTEXT_TURN_LIMIT = 5

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


# ── A2A client ────────────────────────────────────────────────────────────────

class HermesA2AClient:
    """
    Minimal A2A client for the Hermes gateway.

    Protocol:
      POST /  with method=message/stream + Accept: text/event-stream
        → SSE stream of JSON-RPC result frames:
            {"result": {"task": {...}}}                 initial ack
            {"result": {"statusUpdate": {...}}}         state changes
            {"result": {"artifactUpdate": {...}}}       streamed text chunks
            : done                                      stream end sentinel
      Pass contextId in params to continue an existing conversation.
    """

    def __init__(self, base_url: str):
        self._base   = base_url.rstrip("/")
        self._http   = requests.Session()
        self._req_id = 1

    # ── health ────────────────────────────────────────────────────────────────

    def get_agent_card(self) -> dict:
        r = self._http.get(
            f"{self._base}/.well-known/agent-card.json", timeout=10
        )
        r.raise_for_status()
        return r.json()

    def is_healthy(self) -> bool:
        try:
            return bool(self.get_agent_card())
        except Exception:
            return False

    # ── streaming send ────────────────────────────────────────────────────────

    def send_stream(
        self,
        text: str,
        context_id: Optional[str] = None,
        timeout: float = 120.0,
        on_chunk=None,
        on_status=None,
    ) -> dict:
        """
        Send a user message via message/stream.

        Returns a dict with keys:
          context_id  str   – use for subsequent turns
          task_id     str
          text        str   – full assembled response text
          state       str   – final TASK_STATE_*
        """
        params: dict = {
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": text}],
            }
        }
        if context_id:
            params["contextId"] = context_id

        body = {
            "jsonrpc": "2.0",
            "method": "message/stream",
            "params": params,
            "id": self._req_id,
        }
        self._req_id += 1

        # Use a short per-chunk read timeout so a hung SSE stream (e.g. after
        # the gateway's anti-loop kicks in) doesn't block the client forever.
        chunk_read_timeout = min(30.0, timeout)

        resp = self._http.post(
            f"{self._base}/",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            stream=True,
            timeout=(10, chunk_read_timeout),
        )
        resp.raise_for_status()

        result = {"context_id": context_id, "task_id": "", "text": "", "state": ""}
        artifact_parts: dict[str, list[str]] = {}  # artifactId → accumulated text parts

        for raw_line in resp.iter_lines(decode_unicode=True):
            if not raw_line:
                continue
            if raw_line.startswith(": "):
                # SSE comment / done sentinel
                continue
            if raw_line.startswith("data: "):
                data_str = raw_line[len("data: "):]
                try:
                    frame = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                if "error" in frame:
                    err = frame["error"]
                    msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                    raise RuntimeError(f"A2A error: {msg}")

                r = frame.get("result", {})

                if "task" in r:
                    t = r["task"]
                    result["task_id"]    = t.get("id", "")
                    result["context_id"] = t.get("contextId", context_id)

                elif "statusUpdate" in r:
                    su    = r["statusUpdate"]
                    state = su.get("status", {}).get("state", "")
                    result["state"] = state
                    if result["context_id"] is None:
                        result["context_id"] = su.get("contextId")
                    if on_status:
                        on_status(state)
                    # INPUT_REQUIRED delivers its reply text here, not via artifactUpdate
                    status_msg = su.get("status", {}).get("message", {})
                    for part in status_msg.get("parts", []):
                        chunk = part.get("text", "")
                        if chunk:
                            artifact_parts.setdefault("__status__", []).append(chunk)
                            if on_chunk:
                                on_chunk(chunk)

                elif "artifactUpdate" in r:
                    au  = r["artifactUpdate"]
                    aid = au.get("artifact", {}).get("artifactId", "")
                    parts = au.get("artifact", {}).get("parts", [])
                    for part in parts:
                        chunk = part.get("text", "")
                        if chunk:
                            artifact_parts.setdefault(aid, []).append(chunk)
                            if on_chunk:
                                on_chunk(chunk)

        # assemble final text from all artifact parts in insertion order
        all_text = "".join(
            "".join(chunks) for chunks in artifact_parts.values()
        )
        result["text"] = all_text
        return result

    def close(self):
        self._http.close()


# ── rendering helpers ─────────────────────────────────────────────────────────

def _print_chunk(text: str):
    print(text, end="", flush=True)


def _banner(server_url: str, card: dict):
    w = 52
    print()
    print(_c(BOLD + CYAN, "  Hermes A2A Chat"))
    print(_c(DIM, "  " + "─" * w))
    print(_c(DIM, f"  Server  : {server_url}"))
    print(_c(DIM, f"  Agent   : {card.get('name')} v{card.get('version')}"))
    caps = card.get("capabilities", {})
    print(_c(DIM, f"  Stream  : {caps.get('streaming', False)}"))
    skills = card.get("skills", [])
    print(_c(DIM, f"  Skills  : {len(skills)} toolsets"))
    print(_c(DIM, "  " + "─" * w))
    print(_c(DIM, "  Type a message and press Enter."))
    print(_c(DIM, "  /quit  /session  /new  /skills"))
    print(_c(DIM, "  " + "─" * w))
    print()


# ── chat session ──────────────────────────────────────────────────────────────

def run_chat(server_url: str) -> int:
    print(_c(BOLD, f"\nConnecting to {server_url}…"), flush=True)

    client = HermesA2AClient(server_url)

    try:
        card = client.get_agent_card()
    except Exception as exc:
        print(_c(RED, f"Cannot reach gateway: {exc}"))
        return 1

    print(_c(GREEN, f"  Connected to {card.get('name')} v{card.get('version')}"))

    _banner(server_url, card)

    context_id: Optional[str] = None
    turn_count  = 0   # turns used on the current context
    last_response = ""

    try:
        while True:
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
                if context_id:
                    print(_c(DIM, f"  Context ID : {context_id}"))
                    print(_c(DIM, f"  Turns used : {turn_count}/{CONTEXT_TURN_LIMIT}"))
                else:
                    print(_c(DIM, "  No active context (no messages sent yet)."))
                continue

            if user_input.lower() == "/new":
                context_id  = None
                turn_count  = 0
                last_response = ""
                print(_c(YELLOW, "  New conversation started."))
                continue

            if user_input.lower() == "/skills":
                skills = card.get("skills", [])
                print(_c(DIM, f"  {len(skills)} toolsets:"))
                for s in skills:
                    sid   = s.get("id", "").replace("toolset.", "")
                    tags  = s.get("tags", [])
                    print(f"    • {_c(CYAN, sid)}: {len(tags)} ops")
                continue

            # ── send to Hermes ─────────────────────────────────────────────────

            # Rotate context before hitting the gateway's anti-loop limit.
            if context_id and turn_count >= CONTEXT_TURN_LIMIT:
                print(_c(YELLOW,
                    f"  [context rotated — gateway limit of {CONTEXT_TURN_LIMIT} turns reached]"))
                context_id = None
                turn_count = 0

            in_response = [False]

            def on_chunk(text: str):
                if not in_response[0]:
                    print(_c(CYAN, "\nHermes: "), end="", flush=True)
                    in_response[0] = True
                _print_chunk(text)

            def on_status(state: str):
                pass  # state transitions are visible via streaming chunks

            try:
                result = client.send_stream(
                    user_input,
                    context_id=context_id,
                    on_chunk=on_chunk,
                    on_status=on_status,
                )
            except Exception as exc:
                if in_response[0]:
                    print()
                print(_c(RED, f"\nError: {exc}"))
                print()
                continue

            if in_response[0]:
                print()  # newline after streamed response

            context_id    = result["context_id"] or context_id
            turn_count   += 1
            last_response = result["text"]

            state = result.get("state", "")
            if state and state not in ("TASK_STATE_COMPLETED",):
                print(_c(DIM, f"  [{state}]"))

            print()

    except KeyboardInterrupt:
        print()

    print(_c(DIM, "\nDisconnecting…"))
    client.close()
    print(_c(BOLD, "Goodbye!"))
    return 0


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Interactive chat client for the Hermes A2A gateway.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 a2a_chat.py
  python3 a2a_chat.py --server http://localhost:9900

Chat commands:
  /quit          exit
  /session       show current context ID
  /new           start a fresh conversation (new context)
  /skills        list available toolsets
        """,
    )
    parser.add_argument(
        "--server", "-s",
        default="http://127.0.0.1:9900",
        metavar="URL",
        help="Hermes A2A gateway URL (default: http://127.0.0.1:9900)",
    )
    args = parser.parse_args()
    sys.exit(run_chat(args.server))


if __name__ == "__main__":
    main()
