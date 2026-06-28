# Claude Agent Harness

A self-contained, file-based AI agent platform built on the **Claude Agent SDK**.
Define the agent's task in `agent/instruction.md`, drop job payload files into
`input/`, run the agent, and collect results from `output/` — via a browser UI
with live log streaming, or fully headless in a container.

Built per [PROJECT-SPEC.md](PROJECT-SPEC.md).

## Two Entry Points

| Mode | Command | Use case |
|------|---------|----------|
| **Web UI** | `python web_app.py` → http://localhost:8080 | Interactive development, demos, workshops |
| **Headless** | `python agent_harness.py` (or container) | CI/CD pipelines, automated batch jobs |

## Architecture

```
Browser (index.html)
  │  HTTP + SSE
  ▼
web_app.py ──── Flask REST API, file management, settings, SSE log stream
  │  import
  ▼
agent_harness.py ── core agent logic, one of three provider paths:
  ├─ anthropic          → claude-agent-sdk (MCP tools, metrics, cost)
  ├─ openrouter         → anthropic SDK with OpenRouter base_url, manual loop
  └─ openai-compatible  → OpenAI chat-completions over httpx (Ollama, LM Studio, vLLM …)
```

The agent interacts with the world only through six scoped tools:
`list_input_files`, `read_input_file`, `write_output`, `append_output`,
`list_output_files`, and `run_command` (shell, can be disabled).

## Folder Model

| Folder | Who writes | Contents |
|--------|-----------|----------|
| `agent/` | You (editable in the UI) | `instruction.md` (**required**), skill `.md` files appended to the system prompt, optional `skills/*.py` tools |
| `input/` | You (editable in the UI) | Job payload files — CSV, JSON, YAML, text, logs, … |
| `output/` | The agent | Result files + `agent.log` (read-only in the UI) |

`agent/` is the agent's brain (*what to do*); `input/` is the job's data
(*what to work on*). One agent configuration can be reused across many input
batches.

## Quick Start (Web UI)

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt

# Set at least one key (or enter it later in the web UI):
export ANTHROPIC_API_KEY="sk-ant-..."   # Linux/Mac
$env:ANTHROPIC_API_KEY = "sk-ant-..."   # Windows PowerShell

python web_app.py
# → http://localhost:8080
```

> **Note:** the `anthropic` provider path uses the Claude Agent SDK, which
> drives the Claude Code CLI under the hood — Node.js must be available on the
> host. The `openrouter` and `openai-compatible` paths are pure HTTP and have
> no such requirement.

A sample job ships in the repo: `agent/instruction.md` summarizes the files in
`input/`. Click **Run** and watch the Logs tab; results appear in `output/`.

## Quick Start (Headless)

```bash
AGENT_DIR=./agent INPUT_DIR=./input OUTPUT_DIR=./output python agent_harness.py
```

Exits `0` on success, `1` on any error. Logs go to stdout and `output/agent.log`.

## Container (Headless)

```bash
podman build -t claude-agent-headless -f Containerfile .

podman run --rm \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -v ./agent:/app/agent \
  -v ./input:/app/input \
  -v ./output:/app/output \
  claude-agent-headless
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Required for the `anthropic` provider |
| `OPENROUTER_API_KEY` | — | Required for the `openrouter` provider |
| `OPENAI_API_KEY` | — | Optional bearer token for `openai-compatible` |
| `OPENAI_BASE_URL` | `http://localhost:11434/v1` | OpenAI-compatible endpoint (Ollama default) |
| `API_PROVIDER` | `anthropic` | `anthropic` \| `openrouter` \| `openai-compatible` |
| `MODEL` | `claude-opus-4-5` | Model ID |
| `MAX_TURNS` | `50` | Max agentic loop iterations |
| `AGENT_DIR` / `INPUT_DIR` / `OUTPUT_DIR` | `./agent` etc. (web), `/app/...` (headless) | Folder paths |
| `ALLOW_SHELL` | `true` | Set `false` to disable the `run_command` tool |
| `SHELL_TIMEOUT` | `60` | Max seconds a single shell command may run |
| `PORT` / `HOST` | `8080` / `0.0.0.0` | Web UI bind |

Provider, model, API keys, max turns, shell settings, and the
OpenAI-compatible base URL can all be changed live in the web UI (🔑 and ⚙
buttons) — no restart needed. Keys are held in process memory only and are
never sent back to the browser.

## Web UI

- **Three file panels** (AGENT / INPUT / OUTPUT) with upload, create, edit,
  delete, and clear; panels are drag-resizable. `output/` is read-only.
- **File Viewer tab** — in-browser editor with Ctrl+S save and dirty-state
  indicator; syntax-highlighted read-only view for output files.
- **Logs tab** — dark terminal streaming the run live over SSE, colour-coded
  by `[tool_use]` / `[result]` / `[assistant]` / errors, with auto-scroll.
- **Metrics** — after each run: duration, turns, cost (Anthropic path),
  input/output token totals, and output file count, shown in the header chip
  and the OUTPUT panel card.
- **Job history** — last 20 runs persisted to `output/.job_history.json`,
  available at `GET /api/jobs`.

## REST API

See [PROJECT-SPEC.md §6.3](PROJECT-SPEC.md) for the full table. Highlights:

| Method & path | Purpose |
|---------------|---------|
| `GET/PUT/POST/DELETE /api/file/<folder>/<path>` | Read / save / create / delete files |
| `POST /api/upload/<folder>` | Multipart upload (agent, input) |
| `GET /api/providers` · `POST /api/provider` | List / switch provider |
| `GET /api/models?provider=` · `POST /api/model` | Live model list (5-min cache) / select model |
| `GET/POST /api/keys` | Key presence (booleans only) / set key |
| `GET/POST /api/settings` | Max turns, shell, OpenAI-compatible base URL |
| `POST /api/agent/run` · `POST /api/agent/reset` | Start / reset a run |
| `GET /api/agent/status` · `GET /api/agent/logs` | Status + metrics / SSE log stream |
| `GET /api/jobs` | Job history (last 20 runs) |

## Workshop Extension Points

`agent_harness.py` contains three clearly marked exercise sections:

| Exercise | Hook | Default behaviour |
|----------|------|-------------------|
| **3 — Custom Tools** | `CUSTOM_TOOLS` / `CUSTOM_TOOL_NAMES` | Empty — add `@tool`-decorated functions |
| **4 — Guardrail Agent** | `run_guardrail_check()` | Pass-through — implement an LLM judge that blocks unsafe instructions |
| **5 — Skill Loader** | `load_skills()` | Returns nothing — scan `agent/skills/*.py` for extra tools |

Each section includes a skeleton signature and a commented example implementation.

## Security

- Every file path is resolved and checked against its base folder — path
  traversal is rejected in both the web layer and the agent tools.
- Upload filenames are sanitised (`[^\w.\-/]` → `_`).
- API keys are never returned to the browser (presence booleans only).
- The Anthropic path disallows the SDK's built-in `Read`/`Write`/`Edit`/
  `MultiEdit`/`WebSearch` tools; the agent only gets the six scoped tools.
- Shell commands run in `output/`, are bounded by `SHELL_TIMEOUT`, and can be
  disabled entirely with `ALLOW_SHELL=false`.
- The container runs as non-root UID 1001 with volumes for the three folders only.

## Project Layout

```
sdk-agent/
├── agent_harness.py     Core agent logic — both entry points use this
├── web_app.py           Flask web server (REST API + SSE)
├── templates/
│   └── index.html       Single-page web UI (vanilla JS, no build step)
├── agent/
│   └── instruction.md   Task instructions (required)
├── input/               Job payload files
├── output/              Agent results + agent.log
├── requirements.txt
├── Containerfile        Headless UBI9 container
├── PROJECT-SPEC.md      Full specification
└── README.md
```
