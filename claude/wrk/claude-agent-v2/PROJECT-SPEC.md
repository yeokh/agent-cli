# Claude Agent Harness — Project Specification

**Target:** A coding agent can read this document and produce a working project from scratch.  
**Scope:** `./` only — the Flask web UI variant plus a headless container-only runner.
**Detail level:** Architecture + interfaces. Coding agent fills in all implementations.

---

## 1. Overview

The Claude Agent Harness is a self-contained, file-based AI agent platform built on the **Claude Agent SDK** (`claude-agent-sdk`). It exposes two entry points:

| Mode | File | Trigger | Use case |
|------|------|---------|----------|
| **Web UI** | `web_app.py` | `python web_app.py` → browser at `http://localhost:8080` | Interactive development, demos, workshops |
| **Headless** | `agent_harness.py` | `python agent_harness.py` (or container) | CI/CD pipelines, automated batch jobs |

The agent follows a single workflow: read `agent/instruction.md` (plus any skill `.md` files and scripts in `agent/`), read job payload files from `input/`, produce output files in `output/`.

---

## 2. File Layout

```
project-folder/
├── agent_harness.py        # Core agent logic — both entry points use this
├── web_app.py              # Flask web server
├── templates/
│   └── index.html          # Single-page web UI
├── agent/                  # Runtime: instruction.md, skill .md files, scripts
│   └── instruction.md      # Required — task instructions for the agent
├── input/                  # Runtime: job payload files (CSV, JSON, text, tar etc.)
├── output/                 # Runtime: agent outputs + agent.log
├── requirements.txt
├── Containerfile           # Headless container (no web UI)
└── PROJECT-SPEC.md         # This file
```

### Folder Roles

| Folder | Who writes | Who reads | Contents |
|--------|-----------|-----------|----------|
| `agent/` | User (via UI or directly) | Agent reads; **editable via UI** | `instruction.md` (required), skill `.md` files, Python scripts loaded as tools |
| `input/` | User (via UI or directly) | Agent reads; **editable via UI** | Job payload files — CSV, JSON, YAML, text, logs, etc. |
| `output/` | Agent writes | User reads (read-only in UI) | Produced files + `agent.log` |

The `agent/` folder is the agent's "brain" — it defines *what* the agent does and *how*.  
The `input/` folder is the job's data — it defines *what* the agent works on.  
These are separated so a single agent configuration can be reused across multiple input batches.

---

## 3. Dependencies (`requirements.txt`)

```
claude-agent-sdk>=0.1.80
anthropic>=0.30.0
anyio>=4.0.0
flask>=3.0.0
httpx>=0.27.0
mcp>=1.27.0
werkzeug>=3.1.0
```

---

## 4. Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Required for Anthropic provider |
| `OPENROUTER_API_KEY` | — | Required for OpenRouter provider |
| `API_PROVIDER` | `anthropic` | `anthropic` or `openrouter` |
| `MODEL` | `claude-opus-4-5` | Model ID |
| `MAX_TURNS` | `50` | Max agentic loop iterations |
| `AGENT_DIR` | `/app/agent` | Path to agent folder (instruction + skills) |
| `INPUT_DIR` | `/app/input` | Path to input folder (job payloads) |
| `OUTPUT_DIR` | `/app/output` | Path to output folder |
| `ALLOW_SHELL` | `true` | Set `false` to disable `run_command` tool |
| `SHELL_TIMEOUT` | `60` | Max seconds a single shell command may run |
| `PORT` | `8080` | Web UI port |
| `HOST` | `0.0.0.0` | Web UI bind address |

Include support for OpenAI compatible local providers/models.
Provide the web UI to update the variables such as the API Key, API PROVIDER and MAX_TURNS.

---

## 5. `agent_harness.py` — Core Agent Logic

### 5.1 Public Interface

```python
async def run_agent(
    agent_dir: Path,
    input_dir: Path,
    output_dir: Path,
    log_callback: Callable[[str], None] | None = None,
    stats_out: dict | None = None,
) -> None
```

Dispatches to `_run_agent_anthropic` or `_run_agent_openrouter` based on `API_PROVIDER`.  
Emits log lines via `log_callback` if provided (used by the web app for SSE streaming).  
Populates `stats_out` with `total_turns` and `total_cost_usd` when available (Anthropic path).

### 5.2 Agent Folder Loading

Before running the agentic loop, load the `agent/` folder:

1. **`agent/instruction.md`** — required. Read as the task instructions. Raise `FileNotFoundError` if absent.
2. **`agent/*.md`** (excluding `instruction.md`) — optional skill files. Their contents are appended to the system prompt under a `## Skills` heading, in filename-sorted order.
3. **`agent/skills/*.py`** — optional Python scripts. Loaded dynamically as additional tools (Exercise 5 — Skill Loader).

The instruction file path is `agent_dir / "instruction.md"`. All other `.md` files in `agent_dir` (not in subdirs) are skill reference documents appended to the prompt.

### 5.3 Core Agent Tools

The agent has six tools covering file I/O and shell execution.

#### File I/O tools (5)

| Tool name | Args | Returns | Behaviour |
|-----------|------|---------|-----------|
| `list_input_files` | — | JSON array of strings | All files in input folder |
| `read_input_file` | `path: str` | file contents as text | Validates path stays within input (no traversal) |
| `write_output` | `path: str, content: str` | confirmation string | Writes/overwrites a file in output; creates parent dirs |
| `append_output` | `path: str, content: str` | confirmation string | Appends to output file (creates if absent) |
| `list_output_files` | — | JSON array of strings | All files in output, excluding `agent.log` |

File I/O security invariant: every tool that takes a `path` must call `(base / rel).resolve()` and verify the result starts with `str(base.resolve())`. Raise `ValueError("Path traversal denied")` if not.

#### Shell tool (1)

| Tool name | Args | Returns | Behaviour |
|-----------|------|---------|-----------|
| `run_command` | `command: str`, `timeout: int` (optional, default 60) | `{"stdout": str, "stderr": str, "returncode": int}` | Executes a shell command; captures output |

**Implementation (`_tool_run_command`):**

```python
async def _tool_run_command(args: dict) -> str:
    command = args["command"]
    timeout = int(args.get("timeout", 60))
    proc = await anyio.run_process(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # If timeout expires, kill the process and return error
    result = {
        "stdout":     proc.stdout.decode("utf-8", errors="replace"),
        "stderr":     proc.stderr.decode("utf-8", errors="replace"),
        "returncode": proc.returncode,
    }
    return json.dumps(result)
```

Use `anyio.fail_after(timeout)` to enforce the timeout. On `TimeoutError`, kill the process and return `{"stdout": "", "stderr": "Command timed out", "returncode": -1}`.

Log the command and its return code at INFO level: `[tool] run_command(%s) -> rc=%d`.  
Log the first 200 chars of stdout/stderr at DEBUG level.

**Shell access is enabled by default.** It can be disabled by setting `ALLOW_SHELL=false` in the environment. When disabled, `run_command` returns an error string `"Shell access is disabled (ALLOW_SHELL=false)"` without executing anything, and a warning is logged.

The system prompt is updated when shell is enabled to include `run_command` in the tool list and a note about its availability (see §5.5).

#### Disallowed tools (Anthropic path)

With shell enabled, remove `"Bash"` from `disallowed_tools` since the agent now has its own scoped `run_command` instead. Keep the rest: `["Read","Write","Edit","MultiEdit","WebSearch"]`.

### 5.4 Provider Paths

**Anthropic path** — uses `claude_agent_sdk`:
- Build tools with `make_tools(input_dir, output_dir)` using the `@tool` decorator.
- Create an MCP server with `create_sdk_mcp_server(name="agent-tools", ...)`.
- Configure `ClaudeAgentOptions` with `disallowed_tools=["Read","Write","Edit","Bash","MultiEdit","WebSearch"]` and `permission_mode="acceptEdits"`.
- Run `ClaudeSDKClient.query("Begin executing the task instructions now.")` and consume `receive_response()`.
- On each `ResultMessage`, log: turns, cost (USD), stop reason. Populate `stats_out`.

**OpenRouter path** — uses `anthropic` SDK with custom `base_url`:
- `base_url="https://openrouter.ai/api"`, pass `HTTP-Referer` and `X-Title` headers.
- Manual agentic loop: send messages → receive response → dispatch tool calls → repeat.
- Loop terminates when `stop_reason == "end_turn"` or `max_turns` is reached.
- Each turn: log turn number and stop reason.

### 5.5 System Prompt

```
You are a capable, autonomous AI agent running inside a secure container.
You interact with the world ONLY through the tools listed below —
never use built-in Read/Write/Edit/Bash tools.

Available tools:
  • list_input_files  – list payload files in the input folder
  • read_input_file   – read a file from the input folder
  • write_output      – write a file to the output folder
  • append_output     – append to a file in the output folder
  • list_output_files – list files already written to the output folder
  • run_command       – execute a shell command; returns stdout, stderr, returncode
  [• <custom_skill_name>  (custom skill)]  ← injected for loaded skills

Shell guidance:
  - Prefer targeted commands (grep, awk, python, jq, curl, ansible-lint, etc.)
    over broad destructive ones.
  - Working directory for commands is the output folder.
  - Write command output to the output folder via write_output when it should
    be persisted; stdout returned by run_command is ephemeral.
  - Commands time out after <SHELL_TIMEOUT> seconds (default: 60).

[SHELL ACCESS DISABLED — run_command will return an error.]
← This line is only included when ALLOW_SHELL=false

## Skills
<contents of each agent/*.md skill file, labelled by filename>

TASK INSTRUCTIONS:
<contents of agent/instruction.md>
```

The shell guidance block is always present when `ALLOW_SHELL=true` (default).  
When `ALLOW_SHELL=false`, replace the entire shell guidance block with the single disabled notice line.  
`<SHELL_TIMEOUT>` is substituted with the value of env var `SHELL_TIMEOUT` (default `60`).

### 5.6 Extension Points

These three extension points are **explicitly commented placeholders** in the source — workshop participants implement them:

**Exercise 3 — Custom Tools**
```python
CUSTOM_TOOLS: list = []           # add @tool-decorated async functions here
CUSTOM_TOOL_NAMES: list[str] = [] # matching "mcp__agent-tools__<name>" strings
```

**Exercise 4 — Guardrail Agent**
```python
async def run_guardrail_check(instructions: str, input_files: list[str]) -> tuple[bool, str]:
    # Default: pass-through (returns True, "Guardrail pass-through (not implemented)")
    # Workshop: call claude-haiku as a judge; return (is_safe, reason)
```
This function is called before the main agent runs. If it returns `(False, reason)`, raise `RuntimeError(f"Guardrail blocked the run: {reason}")`.

**Exercise 5 — Skill Loader**
```python
def load_skills(agent_dir: Path) -> tuple[list, list[str]]:
    # Default: returns ([], [])
    # Workshop: scan agent/skills/*.py, import each, collect @tool-decorated callables
```

### 5.7 Standalone Entry Point

When run as `python agent_harness.py`:
- Read `AGENT_DIR`, `INPUT_DIR`, `OUTPUT_DIR` from env (defaults: `/app/agent`, `/app/input`, `/app/output`).
- Configure `logging.basicConfig` to write both to `output/agent.log` and `stdout`.
- Print a startup banner with timestamp, provider, model, max_turns.
- Call `run_agent(agent_dir, input_dir, output_dir)`.
- Exit with code 1 on `FileNotFoundError`, `RuntimeError` (guardrail), or SDK errors.

---

## 6. `web_app.py` — Flask Web Server

### 6.1 `AgentState` Class

Thread-safe state container. Fields:

| Field | Type | Values |
|-------|------|--------|
| `status` | str | `idle` \| `running` \| `completed` \| `error` |
| `logs` | `deque[dict]` | maxlen=2000; each entry `{"time": ISO8601, "msg": str}` |
| `started_at` | str \| None | ISO8601 UTC timestamp |
| `finished_at` | str \| None | ISO8601 UTC timestamp |
| `error` | str \| None | error message |
| `metrics` | dict \| None | **NEW** — see §6.2 |

Methods (all acquire `threading.Lock`):
- `start()` — set status=running, clear logs, record started_at
- `finish(error=None)` — set status, record finished_at, set error
- `reset()` — return to idle, clear all fields
- `add_log(message: str)` — append to deque
- `snapshot(offset=0) -> dict` — return serialisable copy, logs[offset:]

### 6.2 Job Metrics (NEW)

After each completed or failed run, compute and store on `AgentState.metrics`:

```python
{
    "duration_seconds": float,       # finished_at - started_at
    "total_turns": int | None,       # from ResultMessage.num_turns (Anthropic path)
    "total_cost_usd": float | None,  # from ResultMessage.total_cost_usd (Anthropic path)
    "log_lines": int,                # len(state.logs) at finish
    "output_files": int,             # count of files in outbox at finish
    "status": "completed" | "error"
}
```

The Anthropic path already receives a `ResultMessage` with `num_turns` and `total_cost_usd` — capture those and pass them back to the web layer via a mutable dict argument or a thin dataclass.

Surface metrics:
- On the status badge in the header: `"Completed · 12 turns · $0.023 · 14.2s"` (or a subset if fields are None).
- In `GET /api/agent/status` response — add a `"metrics"` key.
- Persist the last 20 job runs to `outbox/.job_history.json` (append on each finish).

### 6.3 REST API

All routes return `application/json` unless noted.

#### File Browser & Editor

| Method | Path | Request | Response |
|--------|------|---------|----------|
| `GET` | `/api/agent` | — | `{"files": [{name, size, modified}]}` |
| `GET` | `/api/input` | — | `{"files": [{name, size, modified}]}` |
| `GET` | `/api/output` | — | `{"files": [{name, size, modified}]}` |
| `GET` | `/api/file/agent/<path>` | — | `{"name", "content"}` or 404 |
| `GET` | `/api/file/input/<path>` | — | `{"name", "content"}` or 404 |
| `GET` | `/api/file/output/<path>` | — | `{"name", "content"}` or 404 |
| `PUT` | `/api/file/agent/<path>` | `{"content": str}` | `{"name", "size"}` — **save edits** |
| `PUT` | `/api/file/input/<path>` | `{"content": str}` | `{"name", "size"}` — **save edits** |
| `POST` | `/api/upload/agent` | `multipart/form-data` with `file` | `{"name", "size"}` |
| `POST` | `/api/upload/input` | `multipart/form-data` with `file` | `{"name", "size"}` |
| `POST` | `/api/file/agent` | `{"name": str, "content": str}` | `{"name", "size"}` — **create new file** |
| `POST` | `/api/file/input` | `{"name": str, "content": str}` | `{"name", "size"}` — **create new file** |
| `DELETE` | `/api/file/agent/<path>` | — | `{"deleted": path}` |
| `DELETE` | `/api/file/input/<path>` | — | `{"deleted": path}` |
| `DELETE` | `/api/agent` | — | `{"cleared": true}` |
| `DELETE` | `/api/input` | — | `{"cleared": true}` |
| `DELETE` | `/api/output` | — | `{"cleared": true}` |

`PUT` routes write the `content` string directly to the file (UTF-8). They accept edits from the in-browser editor.  
`POST /api/file/<folder>` creates a new named file — used by the "New file" button in the editor UI.  
`output/` files are **read-only** — no upload, PUT, or DELETE per-file routes exist for `output/`.  
Filename sanitisation: replace any char not in `[A-Za-z0-9._\-/]` with `_`.

#### Provider & Model

| Method | Path | Request | Response |
|--------|------|---------|----------|
| `GET` | `/api/providers` | — | `{"providers": [...], "current": str}` |
| `GET` | `/api/provider` | — | `{"provider": str}` |
| `POST` | `/api/provider` | `{"provider": str}` | `{"provider": str}` or 400 |
| `GET` | `/api/models` | `?provider=` | `{"models": [{id, name}], "provider": str}` |
| `GET` | `/api/model` | — | `{"model": str, "provider": str}` |
| `POST` | `/api/model` | `{"model": str}` | `{"model": str}` |

Model list is fetched live from the provider API with a 5-minute in-process cache:
- **Anthropic:** `GET https://api.anthropic.com/v1/models` with `x-api-key` header.
- **OpenRouter:** `GET https://openrouter.ai/api/v1/models` with `Authorization: Bearer` header.

#### API Key Management (NEW)

| Method | Path | Request | Response |
|--------|------|---------|----------|
| `GET` | `/api/keys` | — | `{"anthropic": bool, "openrouter": bool}` — presence only, never values |
| `POST` | `/api/keys` | `{"provider": str, "key": str}` | `{"ok": true}` |

`POST /api/keys` sets the corresponding env var (`ANTHROPIC_API_KEY` or `OPENROUTER_API_KEY`) in the current process. Keys are **never returned** to the browser — `GET /api/keys` only signals whether each key is set (`bool`). Keys are stored in memory only; they do not survive a server restart unless the user sets them as env vars. Show a key-entry form in the UI when a key is missing.

#### Agent Control

| Method | Path | Request | Response |
|--------|------|---------|----------|
| `POST` | `/api/agent/run` | — | `{"status": "started"}` or 409/400 |
| `POST` | `/api/agent/reset` | — | `{"status": "idle"}` or 409 |
| `GET` | `/api/agent/status` | `?offset=N` | `AgentState.snapshot()` + `"metrics"` key |
| `GET` | `/api/agent/logs` | `?offset=N` | SSE stream |

`POST /api/agent/run` rejects with 409 if `state.status == "running"` and with 400 if `agent/instruction.md` is absent.

The background thread calls `anyio.run(run_agent, AGENT_DIR, INPUT_DIR, OUTPUT_DIR, state.add_log, stats_out)` and calls `state.finish()` in a `finally` block.

#### SSE Log Stream

`GET /api/agent/logs` returns `Content-Type: text/event-stream`.  
Each event payload is a JSON object, one of:
- `{"time": "...", "msg": "..."}` — a log line
- `{"done": true, "status": "completed"|"error"}` — final event; generator returns after this

Poll interval: 0.4 s. Required response headers: `Cache-Control: no-cache`, `X-Accel-Buffering: no`.

### 6.4 Background Thread

```python
def _agent_thread() -> None:
    stats_out = {}
    state.start()
    try:
        anyio.run(run_agent, AGENT_DIR, INPUT_DIR, OUTPUT_DIR, state.add_log, stats_out)
        state.finish(stats=stats_out)
    except FileNotFoundError as exc:
        state.finish(str(exc))
    except RuntimeError as exc:       # guardrail block
        state.finish(str(exc))
    except Exception as exc:
        state.finish(f"Unexpected error: {exc}")
```

Spawned as `threading.Thread(target=_agent_thread, daemon=True)`.

---

## 7. `templates/index.html` — Single-Page Web UI

Single HTML file; no build step; vanilla JS only.

### 7.1 Layout

Two-column CSS grid (`300px left / 1fr right`), with the header spanning full width:

```
┌──────────────────────────────────────────────────────────────┐
│  Header: title · status/metrics · provider · model · Run/Reset│
├────────────────────┬─────────────────────────────────────────┤
│  LEFT COLUMN       │  RIGHT PANEL (toggle)                   │
│  (fixed 300px)     │  (fills remaining width & height)       │
│                    │                                         │
│  ┌──────────────┐  │  [File Viewer] tab  [Logs] tab          │
│  │  AGENT       │  │                                         │
│  │  file list   │  │  ── File Viewer mode ──                 │
│  │  + toolbar   │  │  Editable <textarea> or <pre> viewer    │
│  ├──────────────┤  │  Filename + size + Save / Discard btns  │
│  │  INPUT       │  │                                         │
│  │  file list   │  │  ── Logs mode ──                        │
│  │  + toolbar   │  │  Dark terminal, SSE-streamed log lines  │
│  ├──────────────┤  │  Colour-coded, auto-scroll              │
│  │  OUTPUT      │  │                                         │
│  │  file list   │  │                                         │
│  │  (read-only) │  │                                         │
│  └──────────────┘  │                                         │
└────────────────────┴─────────────────────────────────────────┘
```

The left column has **no fixed row heights** — each section (`AGENT`, `INPUT`, `OUTPUT`) is a flex column that shares the full viewport height equally by default (`flex: 1`). The user can drag the dividers between sections to resize them (CSS `resize` on separators, or simple `flex-basis` drag handles). Each section scrolls independently if its file list overflows.

The right panel fills the remaining height (`height: 100%`). It switches between **File Viewer** and **Logs** via two tab buttons at the top of the panel.

### 7.2 Header

- Title: "Claude Agent Harness"
- Status badge: `idle | running | completed | error` with a coloured dot.
- Metrics chip (visible after completion): `"12 turns · $0.023 · 14.2s"`.
- Provider `<select>` populated from `GET /api/providers`.
- Model `<select>` populated from `GET /api/models?provider=<current>` (re-fetched on provider change).
- **Run** button → `POST /api/agent/run`. Disabled while running.
- **Reset** button → `POST /api/agent/reset`. Disabled while running.

### 7.3 Left Column — Three File Panels

Each panel has the same structure:

```
┌─ AGENT / INPUT / OUTPUT ─────────────────────────────┐
│  Section label + action buttons (Upload, New, Clear)  │
│  ─────────────────────────────────────────────────── │
│  file-row: icon  name  size  [Edit] [Delete]          │
│  file-row: ...                                        │
└───────────────────────────────────────────────────────┘
```

**AGENT panel**
- Lists files from `GET /api/agent`.
- Toolbar: **Upload** (`POST /api/upload/agent`), **New file** (prompts for filename → `POST /api/file/agent`), **Clear** (`DELETE /api/agent`).
- Each file row: click filename → open in File Viewer (editable); delete icon → `DELETE /api/file/agent/<path>`.
- Files with `.md` extension shown with a document icon; `.py` files with a code icon.

**INPUT panel**
- Lists files from `GET /api/input`.
- Toolbar: **Upload** (`POST /api/upload/input`), **New file** (`POST /api/file/input`), **Clear** (`DELETE /api/input`).
- Each file row: click filename → open in File Viewer (editable); delete icon → `DELETE /api/file/input/<path>`.

**OUTPUT panel**
- Lists files from `GET /api/output`.
- Toolbar: **Clear** only (`DELETE /api/output`). No upload, no new file, no per-file delete.
- Each file row: click filename → open in File Viewer (**read-only**).
- Metrics summary card pinned at top of this panel (after a run): duration, turns, cost, file count.

### 7.4 Right Panel — File Viewer tab

Activated when a file is clicked in any left-column panel.

**Editable mode** (agent/ and input/ files):
- `<textarea>` fills the full panel height.
- Header bar shows: filename, file size (updates on save), **Save** button, **Discard** button.
- **Save** → `PUT /api/file/<folder>/<path>` with `{"content": <textarea value>}`. On success: update size, show brief "Saved" confirmation, mark file as clean.
- **Discard** → restore textarea to last-loaded content.
- Unsaved changes indicator (e.g. `●` in tab label or filename bar).
- Keyboard shortcut: `Ctrl+S` / `Cmd+S` triggers Save.

**Read-only mode** (output/ files):
- `<pre>` block with syntax highlighting based on file extension:
  - `.md` → markdown-style (headings bold, code inline monospace)
  - `.json` → JSON key colouring
  - `.py` → Python keyword highlighting
  - `.html` / `.xml` → tag colouring
  - `.log` → same colour rules as terminal (INFO/WARNING/ERROR)
- No Save / Discard buttons.

Falls back to "Select a file to view" placeholder when nothing is selected.

### 7.5 Right Panel — Logs tab

- Dark background (`#0f172a`), monospace font, full panel height.
- Connects to `GET /api/agent/logs` via `EventSource` when a run starts; disconnects on `done` event.
- Colour-codes lines by keyword: `[INFO]` → blue, `[WARNING]` → amber, `[ERROR]`/`BLOCKED`/`FATAL` → red, `[tool_use]` → green, `[result]` → cyan.
- Auto-scrolls to bottom; pauses auto-scroll if the user scrolls up (resumes on scroll-to-bottom).
- **Clear** button clears the DOM display (not the server log).
- When a run starts, automatically switch the right panel to Logs tab.
- When a run completes, show a toast notification and switch back to File Viewer tab if a file was previously open.

### 7.6 API Key Modal

- Shown automatically on page load when `GET /api/keys` shows the active provider's key is missing.
- `<input type="password">` + Save button. Key sent via `POST /api/keys`.
- On success: hide modal, refresh model list.
- Never pre-fill or display a previously entered key.

### 7.7 Polling

- While `status == "running"`: poll `GET /api/agent/status` every 2 s to refresh all three file lists and the status badge.
- On SSE `done` event: final file list refresh, update metrics chip and OUTPUT panel metrics card.

---

## 8. `Containerfile` — Headless Runner

This container runs **only `agent_harness.py`** (no Flask, no web UI).

```dockerfile
FROM registry.access.redhat.com/ubi9/python-312

USER root
RUN microdnf update -y && microdnf clean all

WORKDIR /app
RUN chown 1001:0 /app && chmod g=u /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent_harness.py .

RUN mkdir -p /app/agent /app/input /app/output \
    && chown -R 1001:0 /app/agent /app/input /app/output \
    && chmod -R g=u /app/agent /app/input /app/output

VOLUME ["/app/agent", "/app/input", "/app/output"]

ENV MODEL="claude-opus-4-5" \
    MAX_TURNS="50"                 \
    AGENT_DIR="/app/agent"         \
    INPUT_DIR="/app/input"         \
    OUTPUT_DIR="/app/output"

USER 1001

# No EXPOSE — no web server
CMD ["python", "/app/agent_harness.py"]
```

**Build and run:**
```bash
podman build -t claude-agent-headless -f Containerfile .

podman run --rm \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -v ./agent:/app/agent \
  -v ./input:/app/input \
  -v ./output:/app/output \
  claude-agent-headless
```

The container exits 0 on success, 1 on any error. Results and logs appear in the mounted `output/` volume.

---

## 9. Metrics Collection — Implementation Notes

To propagate `ResultMessage` data from the SDK to the web layer, pass a shared mutable container via `stats_out: dict | None = None`:

```python
# In _run_agent_anthropic:
elif isinstance(msg, ResultMessage):
    if stats_out is not None:
        stats_out["total_turns"]    = msg.num_turns
        stats_out["total_cost_usd"] = msg.total_cost_usd
```

The background thread in `web_app.py` creates `stats_out = {}`, passes it in, and after `anyio.run` completes reads the populated dict to build `AgentState.metrics`.

For the OpenRouter path, `total_turns` and `total_cost_usd` are not available; set them to `None`.

`duration_seconds` is always available: `finished_at - started_at` (parse ISO strings).

---

## 10. Job History (NEW)

After each `state.finish()`, append one entry to `output/.job_history.json`:

```json
[
  {
    "run_id": "2026-06-12T14:23:01Z",
    "status": "completed",
    "provider": "anthropic",
    "model": "claude-opus-4-5",
    "duration_seconds": 14.2,
    "total_turns": 12,
    "total_cost_usd": 0.023,
    "log_lines": 48,
    "output_files": 3
  }
]
```

`run_id` is `started_at`. Read the file before writing to append (not overwrite). Cap history at 20 entries (drop oldest). Expose via `GET /api/jobs` → `{"jobs": [...]}`.

---

## 11. Security Requirements

- **Path traversal**: all `path` parameters must be resolved and checked against their base dir before any read/write.
- **Filename sanitisation**: `[^\w.\-/]` → `_` on upload.
- **API keys**: never returned to the browser; only `bool` presence.
- **Tool lockdown**: `disallowed_tools=["Read","Write","Edit","MultiEdit","WebSearch"]` on the Anthropic path (Bash excluded from the disallow list since the agent uses its own `run_command` tool instead).
- **Shell opt-out**: set `ALLOW_SHELL=false` to disable `run_command` entirely — the tool is still registered but returns an error without executing. Use this for untrusted instruction sources or read-only analysis workloads.
- **Shell timeout**: all commands are bounded by `SHELL_TIMEOUT` (default 60 s). The process is killed on timeout and the tool returns `returncode: -1`.
- **Shell working directory**: commands inherit the process environment. The agent's working directory for commands is the `output/` folder so incidental writes land in a known location.
- **Container**: non-root UID 1001, volumes for agent/input/output only. In containerised deployments, the non-root user naturally limits blast radius of shell commands.

---

## 12. Local Development Setup

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt

# Set at least one key:
export ANTHROPIC_API_KEY="sk-ant-..."   # Linux/Mac
$env:ANTHROPIC_API_KEY = "sk-ant-..."   # Windows PowerShell

# Web UI:
python web_app.py
# → http://localhost:8080

# Headless:
AGENT_DIR=./agent INPUT_DIR=./input OUTPUT_DIR=./output python agent_harness.py
```

---

## 13. Workshop Extension Guide (comments in source)

The source should contain clearly marked comments for three exercises:

```python
# ══════════════════════════════════════════════════════════════════════════════
# WORKSHOP EXERCISE 3 — Add Custom Tools
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# WORKSHOP EXERCISE 4 — Guardrail Agent
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# WORKSHOP EXERCISE 5 — Skill Loader
# ══════════════════════════════════════════════════════════════════════════════
```

Each section should include the skeleton function signature, a docstring describing what the workshop participant should implement, and a commented-out example implementation.

---

