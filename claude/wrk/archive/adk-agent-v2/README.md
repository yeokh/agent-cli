# ADK Agent Harness

A self-contained, file-based AI agent platform built on the **Google Agent
Development Kit (ADK)**.  Define the agent's task in `agent/instruction.md`,
drop job payload files into `input/`, run the agent, and collect results from
`output/` — via a browser UI with live log streaming, or fully headless in a
container.

## Two Entry Points

| Mode | Command | Use case |
|------|---------|----------|
| **Web UI** | `python web_app.py` → http://localhost:8081 | Interactive development, demos, workshops |
| **Headless** | `python adk_agent.py` (or container) | CI/CD pipelines, automated batch jobs |

## Architecture

```
Browser (index.html)
  |  HTTP + SSE
  v
web_app.py ------- Flask REST API, file management, settings, SSE log stream
  |  import
  v
adk_agent.py ----- Google ADK core:
  |                  _build_model()  -> LiteLlm (Anthropic / OpenRouter / OpenAI-compat)
  |                  _make_tools()   -> seven scoped Python functions
  v
LlmAgent + InMemoryRunner
  |  runner.run_async() yields Events
  v
_format_event() -> log lines -> SSE -> browser terminal
```

The agent interacts with the world only through seven scoped tools:
`list_input_files`, `read_input_file`, `write_output`, `append_output`,
`list_output_files`, `run_command` (shell, can be disabled), and `web_fetch`.


## Agent Tools

The agent harness registers the following tools in _make_tools():

    "Available tools:\n"
    "  - list_input_files  -- list payload files in the input folder\n"
    "  - read_input_file   -- read a file from the input folder\n"
    "  - write_output      -- write a file to the output folder\n"
    "  - append_output     -- append to a file in the output folder\n"
    "  - list_output_files -- list files already written to the output folder\n"
    "  - run_command       -- execute a shell command; returns stdout, stderr, returncode\n"
    "  - web_fetch         -- fetch an http(s) URL; returns status, content_type, and text\n"

## Folder Model

| Folder | Who writes | Contents |
|--------|-----------|----------|
| `agent/` | You (editable in the UI) | `instruction.md` (**required**), skill `.md` files appended to the system prompt |
| `input/` | You (editable in the UI) | Job payload files — CSV, JSON, YAML, text, logs, … |
| `output/` | The agent | Result files + `agent.log` (read-only in the UI) |

## Quick Start (Web UI)

```bash
# Create and activate venv (use uv if plain python is not on PATH)
uv venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt

# Set at least one API key (or enter it later in the web UI):
$env:ANTHROPIC_API_KEY = "sk-ant-..."   # Windows PowerShell
export ANTHROPIC_API_KEY="sk-ant-..."   # Linux/Mac

python web_app.py
# -> http://localhost:8081
```

A sample job ships in the repo: `agent/instruction.md` summarizes the files
in `input/`.  Click **Run** and watch the Logs tab; results appear in `output/`.

## Quick Start (Headless)

```bash
AGENT_DIR=./agent INPUT_DIR=./input OUTPUT_DIR=./output python adk_agent.py
```

Exits `0` on success, `1` on any error.  Logs go to stdout and `output/agent.log`.

## Container (Headless)

```bash
podman build -t adk-agent-headless -f Containerfile .

podman run --rm \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -v ./agent:/app/agent \
  -v ./input:/app/input \
  -v ./output:/app/output \
  adk-agent-headless
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Required for the `anthropic` provider |
| `OPENROUTER_API_KEY` | — | Required for the `openrouter` provider |
| `OPENAI_API_KEY` | — | Optional bearer token for `openai-compatible` |
| `OPENAI_BASE_URL` | `http://localhost:11434/v1` | OpenAI-compatible endpoint (Ollama default) |
| `API_PROVIDER` | `anthropic` | `anthropic` \| `openrouter` \| `openai-compatible` |
| `MODEL` | `claude-opus-4-5` | Model ID (as returned by the provider's /models endpoint) |
| `MAX_TURNS` | `50` | Max agentic loop iterations |
| `AGENT_DIR` / `INPUT_DIR` / `OUTPUT_DIR` | `./agent` etc. (web), `/app/...` (headless) | Folder paths |
| `ALLOW_SHELL` | `true` | Set `false` to disable the `run_command` tool |
| `SHELL_TIMEOUT` | `60` | Max seconds a single shell command may run |
| `PORT` / `HOST` | `8081` / `0.0.0.0` | Web UI bind |

## Provider Notes

| Provider | Model ID format | Key variable |
|----------|----------------|--------------|
| `anthropic` | `claude-opus-4-5` | `ANTHROPIC_API_KEY` |
| `openrouter` | `anthropic/claude-opus-4-5` | `OPENROUTER_API_KEY` |
| `openai-compatible` | `llama3.2` (as reported by `/models`) | `OPENAI_API_KEY` (optional) |

All three providers are routed through the ADK **LiteLlm** bridge, so any
LiteLLM-supported model works without code changes.

## Web UI

- **Three file panels** (AGENT / INPUT / OUTPUT) with upload, create, edit,
  delete, and clear; panels are drag-resizable.  `output/` is read-only.
- **File Viewer tab** — in-browser editor with Ctrl+S save and dirty-state
  indicator; syntax-highlighted read-only view for output files.
- **Logs tab** — dark terminal streaming the run live over SSE, colour-coded
  by `[tool_use]` / `[result]` / `[assistant]` / errors, with auto-scroll.
- **Metrics** — after each run: duration, turns, input/output token totals,
  and output file count, shown in the header chip and the OUTPUT panel card.
- **Job history** — last 20 runs persisted to `output/.job_history.json`,
  available at `GET /api/jobs`.

## REST API

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

`adk_agent.py` contains three clearly marked exercise sections:

| Exercise | Hook | Default behaviour |
|----------|------|-------------------|
| **3 — Custom Tools** | `CUSTOM_TOOLS` / `CUSTOM_TOOL_NAMES` | Empty — add plain Python functions with type annotations |
| **4 — Guardrail Agent** | `run_guardrail_check()` | Pass-through — implement an LLM judge that blocks unsafe instructions |
| **5 — Skill Loader** | `load_skills()` | Returns nothing — scan `agent/skills/*.py` for extra tools |

## Security

- Every file path is resolved and checked against its base folder — path
  traversal is rejected in both the web layer and the agent tools.
- Upload filenames are sanitised (`[^\w.\-/]` → `_`).
- API keys are never returned to the browser (presence booleans only).
- Shell commands run in `output/`, are bounded by `SHELL_TIMEOUT`, and can be
  disabled entirely with `ALLOW_SHELL=false`.
- The container runs as non-root UID 1001 with volumes for the three folders only.

## Project Layout

```
adk-agent-v2/
├── adk_agent.py         Core ADK agent logic — both entry points use this
├── web_app.py           Flask web server (REST API + SSE)
├── templates/
│   └── index.html       Single-page web UI (vanilla JS, no build step)
├── agent/
│   └── instruction.md   Task instructions (required)
├── input/               Job payload files
├── output/              Agent results + agent.log
├── requirements.txt
├── Containerfile        Headless UBI9 container
└── README.md
```
