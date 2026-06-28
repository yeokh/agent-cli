Prompt for Cursor Agent:
Please review the project in "./strands-agent" and the web ui of the Flask python program.

This project demonstrate the capability of an AI agent to process all the files in the "inbox" folder, according to the instruction and skill .md files found in the same folder.  And write the output files, including the processing summary log into the "outbox" folder.

I want you to create a new folder in "/root/claude/wrk/claude-agent" and re-implement this project using Claude Agent SDK (https://code.claude.com/docs/en/agent-sdk/overview) as the AI agent.

I want you to keep web_app.py to handle only the web ui based on Flask, and a separate python program for the AI agent based on Claude Agent SDK.

Enable support for OPENROUTER_API_KEY, OPENAI_API_KEY and ANTHROPIC_API_KEY.  Maintain the feature in the web-ui to allow me to edit any file selected from the the "inbox".

This "claude-agent" project will be used for a workshop.  See the "workshop" folder for details. Please read the content and amend it to reflect the workshop for claude-agent.  Please add more comments and workshop placeholders in the python programs.

Ask me anything for any clarification if required.


============================================================================================

# Claude Agent

A web-based file-processing agent powered by the **Claude Agent SDK**.
Drop files into the **inbox**, describe the task in `instruction.md`, hit **Run Agent**,
and collect results from the **outbox** — all via a browser UI with real-time log streaming.
Inbox files can also be edited directly in the browser.

## Architecture

```
Browser (index.html)
  │  HTTP + SSE
  ▼
web_app.py  ─── Flask REST API + SSE log stream + inbox file editor
  │  import
  ▼
claude_agent.py ── Claude Agent SDK (hooks + tool permissions + model registry)
  │  query() + ClaudeAgentOptions
  ▼
Claude API or Gateway  ── Anthropic Claude | OpenAI | OpenRouter (via LiteLLM gateway)
```

**`web_app.py`** handles only HTTP: file management endpoints, inbox file editing,
model selection, agent lifecycle, and SSE streaming. No LLM calls happen here.

**`claude_agent.py`** owns all agent logic: model registry, Claude Agent SDK
configuration, hooks for tool logging, and the streaming log bridge.

## Supported Providers

| Provider | Environment variable | Notes |
|----------|----------------------|-------|
| Anthropic | `ANTHROPIC_API_KEY` | Direct to Claude API |
| OpenAI | `OPENAI_API_KEY` | Requires `GATEWAY_URL` (Anthropic-format gateway) |
| OpenRouter | `OPENROUTER_API_KEY` | Requires `GATEWAY_URL` (Anthropic-format gateway) |

OpenAI/OpenRouter models are routed through a LiteLLM (or Anthropic-format) gateway,
using the gateway URL and the provider API key as the gateway auth token.

## Quick Start

```bash
cd claude-agent

# 1. Create a virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .

# 2. Configure at least one API key
cp .env.example .env
#    edit .env and uncomment the key(s) you have

# 3. Load the env and start the server
export $(grep -v '^#' .env | xargs)   # Linux/macOS
python web_app.py
# or: claude-agent-web
```

Open **http://localhost:8080** in your browser.

## Usage

1. **Upload files** — drag-and-drop or click _Upload file_ to add to inbox.
   `instruction.md` **must** be present to run the agent.
2. **Edit inbox files** — click any inbox file, then click the **✏ Edit** button
   to edit it in-browser. Click **💾 Save** to write the changes back.
3. **Select a model** — pick from available models in the dropdown (bottom-right).
4. **Run Agent** — the agent reads `instruction.md`, processes inbox files, writes to outbox.
5. **View results** — click any outbox file to preview it.
6. **Reset** — click _Reset_ after a run to clear state and start again.

## Claude Agent SDK Notes

- The agent uses Claude Agent SDK built-in tools (`Read`, `Write`, `Edit`, `Glob`, `Grep`, `Bash`).
- Tool calls are logged through SDK hooks so the UI shows `[tool_use]` and `[result]`
  lines just like the earlier Strands/ADK harnesses.
- Hooks block reads/writes outside the inbox/outbox directories and filter unsafe
  Bash patterns. This is a lightweight safeguard, not a sandbox.

## Extending

### Change the task
Edit or replace `inbox/instruction.md` — use the browser editor or upload a new file.

### Add a model
Provider models are fetched dynamically. If your gateway uses custom model IDs, add
them in `claude_agent.py` or set a custom model option via environment variables.

### Add a guardrail or pipeline
See the workshop exercises for guardrails and multi-stage pipelines; placeholders
in `web_app.py` and `claude_agent.py` point to the relevant sections.

## Project Layout

```
claude-agent/
├── web_app.py          Flask web UI (HTTP endpoints + SSE + inbox editor)
├── claude_agent.py     Claude Agent SDK runner (model registry, hooks, streaming)
├── templates/
│   └── index.html      Single-page browser UI with file editor
├── inbox/              Agent reads from here; files editable in browser
│   ├── instruction.md  Task definition (required)
│   └── *.yaml / *.txt  Payload files
├── outbox/             Agent writes to here
│   └── agent.log       Processing summary (written by agent)
├── workshop/           Guided exercises for the workshop
├── .env.example        API key + gateway template
└── pyproject.toml      Dependencies
```
