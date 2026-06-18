I'm in **Ask mode**, so I can't create files on your machine — but here is a complete Python program you can save and run.

---

## Save as `acp_client.py`

```python
#!/usr/bin/env python3
"""
Minimal ACP client for Cursor's `agent acp`.
Spawns agent as subprocess, speaks JSON-RPC over stdin/stdout.
"""

import json
import os
import subprocess
import sys
import threading
from typing import Any

AGENT_CMD = os.environ.get("AGENT_CMD", "agent")
AGENT_ARGS = ["acp"]
WORKSPACE = os.environ.get("ACP_CWD", os.getcwd())


class AcpClient:
    def __init__(self) -> None:
        self._next_id = 1
        self._pending: dict[int, dict[str, Any]] = {}
        self._lock = threading.Lock()

        self.proc = subprocess.Popen(
            [AGENT_CMD, *AGENT_ARGS],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            text=True,
            bufsize=1,
            shell=(os.name == "nt"),  # helps find `agent` on Windows PATH
        )

        self._reader = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader.start()

    def _read_stdout(self) -> None:
        assert self.proc.stdout is not None
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                print(f"[raw stdout] {line}", file=sys.stderr)
                continue
            self._handle_message(msg)

    def _handle_message(self, msg: dict[str, Any]) -> None:
        # Response to our request
        if "id" in msg and ("result" in msg or "error" in msg):
            with self._lock:
                self._pending[msg["id"]] = msg
            if "error" in msg:
                print(f"[error id={msg['id']}] {msg['error']}", file=sys.stderr)
            return

        method = msg.get("method")

        # Streaming updates
        if method == "session/update":
            update = msg.get("params", {}).get("update", {})
            kind = update.get("sessionUpdate")
            if kind == "agent_message_chunk":
                text = update.get("content", {}).get("text", "")
                if text:
                    sys.stdout.write(text)
                    sys.stdout.flush()
            elif kind == "tool_call":
                title = update.get("title") or update.get("toolCallId", "tool")
                print(f"\n[tool start] {title}", file=sys.stderr)
            elif kind == "tool_call_update":
                status = update.get("status")
                if status:
                    print(f"[tool status] {status}", file=sys.stderr)
            else:
                print(f"[session/update] {kind}", file=sys.stderr)
            return

        # Permission requests — auto-approve for testing
        if method == "session/request_permission":
            req_id = msg["id"]
            print("[permission] auto allow-once", file=sys.stderr)
            self._write(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "outcome": {
                            "outcome": "selected",
                            "optionId": "allow-once",
                        }
                    },
                }
            )
            return

        # Cursor extension methods (optional)
        if method == "cursor/ask_question":
            self._write(
                {
                    "jsonrpc": "2.0",
                    "id": msg["id"],
                    "result": {"outcome": {"outcome": "skipped"}},
                }
            )
            return

        if method == "cursor/create_plan":
            self._write(
                {
                    "jsonrpc": "2.0",
                    "id": msg["id"],
                    "result": {"outcome": {"outcome": "accepted"}},
                }
            )
            return

        print(f"[notification] {method}: {json.dumps(msg.get('params', {}))[:200]}", file=sys.stderr)

    def _write(self, payload: dict[str, Any]) -> None:
        assert self.proc.stdin is not None
        line = json.dumps(payload, separators=(",", ":")) + "\n"
        self.proc.stdin.write(line)
        self.proc.stdin.flush()

    def request(self, method: str, params: dict[str, Any], timeout: float = 120.0) -> dict[str, Any]:
        req_id = self._next_id
        self._next_id += 1

        print(f">>> {method} (id={req_id})", file=sys.stderr)
        self._write({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})

        import time

        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                msg = self._pending.pop(req_id, None)
            if msg is not None:
                if "error" in msg:
                    raise RuntimeError(f"{method} failed: {msg['error']}")
                return msg["result"]
            time.sleep(0.01)

        raise TimeoutError(f"Timed out waiting for response to {method} (id={req_id})")

    def close(self) -> None:
        if self.proc.stdin:
            self.proc.stdin.close()
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def abs_cwd(path: str) -> str:
    # JSON-friendly absolute path (forward slashes work on Windows too)
    return os.path.abspath(path).replace("\\", "/")


def bootstrap(client: AcpClient) -> str:
    init = client.request(
        "initialize",
        {
            "protocolVersion": 1,
            "clientCapabilities": {
                "fs": {"readTextFile": False, "writeTextFile": False},
                "terminal": False,
            },
            "clientInfo": {"name": "py-acp-client", "version": "0.1.0"},
        },
    )
    print(f"<<< initialize OK (protocolVersion={init.get('protocolVersion')})", file=sys.stderr)

    client.request("authenticate", {"methodId": "cursor_login"})
    print("<<< authenticate OK", file=sys.stderr)

    session = client.request(
        "session/new",
        {"cwd": abs_cwd(WORKSPACE), "mcpServers": []},
    )
    session_id = session["sessionId"]
    print(f"<<< session/new OK (sessionId={session_id})", file=sys.stderr)
    return session_id


def prompt(client: AcpClient, session_id: str, text: str) -> None:
    print("\n--- assistant ---\n", file=sys.stderr)
    result = client.request(
        "session/prompt",
        {
            "sessionId": session_id,
            "prompt": [{"type": "text", "text": text}],
        },
        timeout=600.0,
    )
    print(f"\n\n--- stopReason={result.get('stopReason')} ---\n", file=sys.stderr)


def interactive_loop(client: AcpClient, session_id: str) -> None:
    print("Interactive mode. Type a prompt and press Enter. Empty line or Ctrl+C to quit.", file=sys.stderr)
    while True:
        try:
            user_text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print(file=sys.stderr)
            break
        if not user_text:
            break
        prompt(client, session_id, user_text)


def main() -> int:
    if len(sys.argv) > 1:
        first_prompt = " ".join(sys.argv[1:])
        mode = "once"
    else:
        first_prompt = None
        mode = "interactive"

    client = AcpClient()
    try:
        session_id = bootstrap(client)

        if mode == "once" and first_prompt:
            prompt(client, session_id, first_prompt)
        else:
            if first_prompt:
                prompt(client, session_id, first_prompt)
            interactive_loop(client, session_id)

    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

---

## How to run

### 1. Prerequisites

```powershell
agent login
# or: $env:CURSOR_API_KEY = "cursor_..."

agent --version
```

### 2. One-shot prompt

```powershell
cd C:\DevWorks
python acp_client.py "Say hello in one sentence. Do not use tools."
```

### 3. Interactive REPL

```powershell
python acp_client.py
```

Example session:

```text
you> What files are in this directory?
you> Now summarize the README
you>          ← empty line quits
```

### 4. Optional env vars

```powershell
$env:ACP_CWD = "C:\DevWorks"      # workspace for session/new
$env:AGENT_CMD = "agent"          # if agent is not on PATH
python acp_client.py "Hello"
```

---

## What the program does

```text
┌─────────────────────┐     stdin/stdout (NDJSON)     ┌──────────────┐
│  acp_client.py      │ ◄──────────────────────────► │  agent acp   │
│                     │                               │              │
│  main thread:       │     stderr (logs)             │  Cursor      │
│    send requests    │ ────────────────────────────► │  agent       │
│                     │                               │              │
│  reader thread:     │                               └──────────────┘
│    session/update   │
│    permissions      │
└─────────────────────┘
```

1. Spawns `agent acp`
2. Runs `initialize` → `authenticate` → `session/new`
3. Sends `session/prompt` for your text
4. Prints streaming assistant text from `session/update`
5. Auto-approves `session/request_permission` (for testing)
6. Supports multiple prompts in interactive mode

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `agent` not found | Install Cursor CLI; set `AGENT_CMD` to full path |
| Auth error | Run `agent login` or set `CURSOR_API_KEY` |
| Hangs on prompt | Agent waiting for permission — script auto-approves; check stderr |
| Timeout | Increase `timeout=` in `prompt()` |
| `session/new` fails | Ensure `ACP_CWD` is a valid absolute workspace path |

---

If you switch to **Agent mode**, I can create `acp_client.py` in your workspace and help you run the first test.
