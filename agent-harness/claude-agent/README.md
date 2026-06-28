# Claude Agent Harness

A file-processing agent harness powered by the **Anthropic Claude SDK** (`claude-agent-sdk`).
Provides both a headless batch mode and a Flask web UI, and supports three LLM provider paths:
`anthropic` (native Claude SDK), `openrouter`, and `openai-compatible`.

---

## Quick Start (local)

```bash
cd agent-harness/claude-agent

# Install dependencies (with uv)
uv sync

# Set your API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Run headless
python claude_agent.py

# Run web UI
python web_app.py
# Then open http://localhost:8080
```

---

## Project Layout

```
claude-agent/
├── claude_agent.py          # Core agent logic (all provider paths)
├── web_app.py               # Flask web UI + REST API
├── templates/index.html     # Web UI template
├── agent/
│   └── instruction.md       # Agent task instructions (required)
├── input/                   # Job payload files (read by agent)
├── output/                  # Agent results + agent.log (written by agent)
├── pyproject.toml
├── Containerfile
├── entrypoint.sh
└── deployment/              # Kubernetes / OpenShift manifests
```

---

## How It Works

1. Place your task instructions in `agent/instruction.md`
2. Drop input files into `input/`
3. Run the agent (headless or via web UI)
4. Collect results from `output/`

The agent has access to seven tools:

| Tool | Description |
|------|-------------|
| `list_input_files` | List files in `input/` |
| `read_input_file` | Read a file from `input/` |
| `write_output` | Write a file to `output/` |
| `append_output` | Append text to a file in `output/` |
| `list_output_files` | List files in `output/` |
| `run_command` | Execute a shell command (working dir: `output/`) |
| `web_fetch` | Fetch an HTTP/HTTPS URL and return the response body |

---

## Provider Support

| `API_PROVIDER` | Authentication | Notes |
|----------------|----------------|-------|
| `anthropic` | `ANTHROPIC_API_KEY` | Native claude-agent-sdk; supports cost tracking |
| `openrouter` | `OPENROUTER_API_KEY` | Anthropic SDK with OpenRouter base URL |
| `openai-compatible` | `OPENAI_API_KEY` (optional) | Any OpenAI-compatible endpoint (`OPENAI_BASE_URL`) |

Switch providers via the web UI or by setting `API_PROVIDER` in the environment.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_PROVIDER` | `anthropic` | LLM provider |
| `MODEL` | `claude-opus-4-5` | Model ID |
| `MAX_TURNS` | `50` | Max agent loop iterations |
| `MAX_OUTPUT_TOKENS` | `16384` | Max tokens per model response (openrouter / openai-compat) |
| `ALLOW_SHELL` | `true` | Enable `run_command` tool |
| `SHELL_TIMEOUT` | `60` | Shell command timeout (seconds) |
| `AGENT_DIR` | `./agent` | Instruction folder |
| `INPUT_DIR` | `./input` | Input payload folder |
| `OUTPUT_DIR` | `./output` | Output folder |
| `PORT` | `8080` | Web UI port |
| `HOST` | `0.0.0.0` | Web UI bind address |
| `RUN_MODE` | `agent` | `agent` = headless, `web` = Flask UI (container) |

---

## Workshop Exercises

The agent harness is designed as a workshop platform. Three extension points are
clearly marked in `claude_agent.py`:

- **Exercise 3 — Custom Tools**: Add your own `@tool`-decorated async functions to `CUSTOM_TOOLS`
- **Exercise 4 — Guardrail Agent**: Implement `run_guardrail_check()` to validate instructions before running
- **Exercise 5 — Skill Loader**: Implement `load_skills()` to dynamically load tools from `agent/skills/*.py`

---

## Container / OpenShift Deployment

See [`deployment/claude-agent-job-instruction.md`](deployment/claude-agent-job-instruction.md) for
full build, push, and OpenShift deployment instructions.

```bash
# Build image
podman build -t quay.io/khyeo/claude-agent:v1 -f Containerfile .
podman push quay.io/khyeo/claude-agent:v1

# Deploy web UI on OpenShift
oc apply -f deployment/secret-api-keys.yaml   # edit first!
oc apply -f deployment/pvc.yaml
oc apply -f deployment/deployment.yaml
oc apply -f deployment/service.yaml
oc apply -f deployment/route.yaml
```
