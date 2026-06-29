# Pydantic AI Agent Harness

A self-contained, file-based AI agent platform built on **[Pydantic AI](https://github.com/pydantic/pydantic-ai)**.
Define the agent's task in `agent/instruction.md`, drop job payload files into `input/`, run the agent,
and collect results from `output/` — via a browser UI with live log streaming, or fully headless in a container.

Supports seven LLM providers out of the box, including locally hosted models via Ollama or vLLM.

## Requirements

- **Python 3.10 or later** (3.11+ recommended; pydantic-ai v2 requires 3.10+)
- pip / uv

## Two Entry Points

| Mode | Command | Use case |
|------|---------|----------|
| **Web UI** | `python web_app.py` → http://localhost:8080 | Interactive development, demos, workshops |
| **Headless** | `python pydantic_agent.py` (or container) | CI/CD pipelines, automated batch jobs |

## Architecture

```
Browser (index.html)
  |  HTTP + SSE
  v
web_app.py ----------- Flask REST API, file management, settings, SSE log stream
  |  import
  v
pydantic_agent.py ---- Pydantic AI core:
  |                      _build_model()  -> provider-specific model instance
  |                      _make_tools()   -> seven scoped Python functions
  v
pydantic_ai.Agent
  |  agent.run_stream_events() yields events
  v
FunctionToolCallEvent / FunctionToolResultEvent / PartDeltaEvent
  -> log lines -> SSE -> browser terminal
```

The agent interacts with the world only through seven scoped tools:
`list_input_files`, `read_input_file`, `write_output`, `append_output`,
`list_output_files`, `run_command` (shell, can be disabled), and `web_fetch`.

## Quick Start (Web UI)

```bash
# Python 3.10+ required — use python3.11 or python3.12 if available
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt

# Set an API key for your chosen provider (or enter it later in the web UI):
export ANTHROPIC_API_KEY="sk-ant-..."

python web_app.py
# Open http://localhost:8080
```

A sample job ships in the repo: `agent/instruction.md` summarises the files in `input/`.
Click **Run** and watch the Logs tab; results appear in `output/`.

## Quick Start (Headless)

```bash
AGENT_DIR=./agent INPUT_DIR=./input OUTPUT_DIR=./output python pydantic_agent.py
```

Exits `0` on success, `1` on any error. Logs go to stdout and `output/agent.log`.

## Supported Providers

| Provider | `API_PROVIDER` value | Default model | API key variable |
|----------|---------------------|--------------|-----------------|
| Anthropic | `anthropic` | `claude-opus-4-5` | `ANTHROPIC_API_KEY` |
| OpenAI | `openai` | `gpt-4o` | `OPENAI_API_KEY` |
| OpenRouter | `openrouter` | `anthropic/claude-opus-4-5` | `OPENROUTER_API_KEY` |
| Gemini | `gemini` | `gemini-2.0-flash` | `GEMINI_API_KEY` |
| Groq | `groq` | `llama-3.1-70b-versatile` | `GROQ_API_KEY` |
| Mistral | `mistral` | `mistral-large-latest` | `MISTRAL_API_KEY` |
| Ollama / vLLM / any OpenAI-compatible | `openai-compatible` | `llama3.2` | `OPENAI_API_KEY` (optional) |

The active provider and model can be switched at any time in the web UI Settings panel without restarting.

### Using Local Models (Ollama / vLLM)

Set the provider to `openai-compatible` and point `OPENAI_BASE_URL` at your local server:

```bash
# Ollama (default base URL — no key needed)
export API_PROVIDER=openai-compatible
export OPENAI_BASE_URL=http://localhost:11434/v1
export MODEL=llama3.2

# vLLM
export API_PROVIDER=openai-compatible
export OPENAI_BASE_URL=http://localhost:8000/v1
export OPENAI_API_KEY=token-abc123   # only if your vLLM server requires a key
export MODEL=mistralai/Mistral-7B-Instruct-v0.3
```

The model list is fetched live from the `/v1/models` endpoint of your local server,
so any model served there will appear in the UI's model dropdown.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_PROVIDER` | `anthropic` | Provider name — see table above |
| `MODEL` | _(provider default)_ | Model ID as returned by the provider |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `OPENAI_API_KEY` | — | OpenAI key; also used as bearer token for `openai-compatible` |
| `OPENROUTER_API_KEY` | — | OpenRouter API key |
| `GEMINI_API_KEY` | — | Google Gemini API key (also accepts `GOOGLE_API_KEY`) |
| `GROQ_API_KEY` | — | Groq API key |
| `MISTRAL_API_KEY` | — | Mistral API key |
| `OPENAI_BASE_URL` | `http://localhost:11434/v1` | Base URL for `openai-compatible` provider |
| `MAX_TURNS` | `50` | Maximum agentic loop iterations |
| `MAX_OUTPUT_TOKENS` | `16384` | Token budget for each model response |
| `AGENT_DIR` | `./agent` (web) / `/app/agent` (container) | Path to the agent folder |
| `INPUT_DIR` | `./input` | Path to the input folder |
| `OUTPUT_DIR` | `./output` | Path to the output folder |
| `ALLOW_SHELL` | `true` | Set `false` to disable the `run_command` tool |
| `SHELL_TIMEOUT` | `60` | Max seconds a single shell command may run |
| `PORT` | `8080` | Web UI bind port |
| `HOST` | `0.0.0.0` | Web UI bind address |
| `RUN_MODE` | `agent` | Container entry point: `agent` (headless) or `web` (Flask UI) |

## Folder Model

| Folder | Who writes | Contents |
|--------|-----------|----------|
| `agent/` | You (editable in the UI) | `instruction.md` (**required**), skill `.md` files appended to the system prompt |
| `input/` | You (editable in the UI) | Job payload files — CSV, JSON, YAML, text, logs, … |
| `output/` | The agent | Result files + `agent.log` (read-only in the UI) |

## Web UI Features

- **Three file panels** (AGENT / INPUT / OUTPUT) with upload, create, edit, delete, and clear; panels are drag-resizable.
- **File Viewer tab** — in-browser editor with Ctrl+S save and dirty-state indicator; syntax-highlighted read-only view for output files.
- **Logs tab** — dark terminal streaming the run live over SSE, colour-coded by `[tool_use]` / `[result]` / `[assistant]` / errors, with auto-scroll.
- **Metrics** — after each run: duration, turns, input/output token totals, and output file count, shown in the header chip and the OUTPUT panel card.
- **Job history** — last 20 runs persisted to `output/.job_history.json`, available at `GET /api/jobs`.
- **Settings panel** — switch provider, model, and API keys live; set `OPENAI_BASE_URL` for local models.

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

## Container

```bash
# Build
podman build -t pydantic-agent -f Containerfile .

# Run as web UI
podman run --rm -it \
  -p 8080:8080 \
  -e RUN_MODE=web \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -v ./agent:/app/agent \
  -v ./input:/app/input \
  -v ./output:/app/output \
  pydantic-agent

# Run headless
podman run --rm \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -v ./agent:/app/agent \
  -v ./input:/app/input \
  -v ./output:/app/output \
  pydantic-agent

# Local model (no key needed)
podman run --rm -it \
  -p 8080:8080 \
  -e RUN_MODE=web \
  -e API_PROVIDER=openai-compatible \
  -e OPENAI_BASE_URL=http://host.containers.internal:11434/v1 \
  -e MODEL=llama3.2 \
  -v ./agent:/app/agent \
  -v ./input:/app/input \
  -v ./output:/app/output \
  pydantic-agent
```

> **Ollama inside a container**: use `http://host.containers.internal:11434/v1` (Podman/Docker on Linux/Mac)
> instead of `localhost`, since `localhost` refers to the container itself.

## Workshop Extension Points

`pydantic_agent.py` contains three clearly marked exercise stubs:

| Exercise | Hook | Default behaviour |
|----------|------|-------------------|
| **3 — Custom Tools** | `CUSTOM_TOOLS` / `CUSTOM_TOOL_NAMES` | Empty — add plain Python functions with type annotations and docstrings |
| **4 — Guardrail Agent** | `run_guardrail_check()` | Pass-through — implement an LLM judge that blocks unsafe instructions |
| **5 — Skill Loader** | `load_skills()` | Returns nothing — scan `agent/skills/*.py` for extra tools |

Pydantic AI infers each tool's JSON schema automatically from type annotations and Google-style docstrings — no decorator magic needed.

## Security

- Every file path is resolved and checked against its base folder — path traversal is rejected in both the web layer and the agent tools.
- Upload filenames are sanitised (`[^\w.\-/]` → `_`).
- API keys are **never** returned to the browser (presence booleans only).
- Shell commands run in `output/`, are bounded by `SHELL_TIMEOUT`, and can be disabled entirely with `ALLOW_SHELL=false`.
- The container runs as non-root UID 1001 with volumes for the three folders only.

## Project Layout

```
pydantic-agent/
├── pydantic_agent.py    Core Pydantic AI agent logic — both entry points use this
├── web_app.py           Flask web server (REST API + SSE)
├── templates/
│   └── index.html       Single-page web UI (vanilla JS, no build step)
├── agent/
│   └── instruction.md   Task instructions (required)
├── input/               Job payload files
├── output/              Agent results + agent.log
├── requirements.txt     Python dependencies (pydantic-ai + provider SDKs)
├── Containerfile        UBI9 Python 3.12 container image
├── entrypoint.sh        Selects web or headless mode via RUN_MODE
├── deployment/
│   └── README.md        Container build and deploy reference
└── README.md
```
