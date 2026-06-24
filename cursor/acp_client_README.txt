https://cursor.com/docs/cli/acp.md

And client application that interact with a Cursor agent via Agent Communication Protocol (ACP).
The Cursor agent starts an ACP server/service via "agent acp" command.

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
│  acp_client.py      │ ◄──────────────────────────►  │  agent acp   │
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
