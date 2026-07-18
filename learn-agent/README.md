# learn-agent

A progressive demo of LLM interaction patterns — from a raw HTTP POST to a
multi-agent agentic system.  Each level is a complete, standalone Python app.

---

## Quick start

```bash
cd /root/learn-agent

# install dependencies
pip3 install -r requirements.txt

# set at least one API key
export OPENROUTER_API_KEY="sk-or-..."   # recommended — gives access to all models
# export OPENAI_API_KEY="sk-..."        # gpt-4o-mini and gpt-4o only
# export ANTHROPIC_API_KEY="sk-ant-..." # claude-haiku-4.5 only

# launch the interactive menu
python3 main.py
```

Or run any level directly:

```bash
python3 level1.py
python3 level2.py
python3 level3.py
python3 level4.py
python3 level5/agent.py
```

---

## Levels

| # | Output label | Tech | Key concept |
|---|---|---|---|
| 1 | `LLM:` (cyan) | `requests` direct POST | Stateless — each request contains only the current message |
| 2 | `Chat:` (blue) | `requests` direct POST | Full history included in every request (context window) |
| 3 | `Chat Assistant:` (green) | Pydantic AI 0.8 | Framework-managed session, system prompt, role separation |
| 4 | `Tool Assistant:` (magenta) | Pydantic AI + tools | ReAct loop — reason, call a tool, observe, repeat |
| 5 | `Agent:` (yellow) | Google ADK + LiteLlm | Multi-agent orchestration with specialised sub-agents |

### Level 1 — Direct HTTP, stateless

A bare `POST /v1/chat/completions` with only the current user message.
The LLM has no memory of prior turns.  A display history is kept locally
so you can read the conversation, but it is never sent to the API.
Demonstrates the difference between a *display log* and a *context window*.

### Level 2 — Direct HTTP, with context

Same raw HTTP approach, but the full conversation history is appended to
every request.  The LLM can now refer back to earlier turns.
A system message is included to ground the assistant.

### Level 3 — Pydantic AI chat

Uses the [pydantic-ai](https://ai.pydantic.dev) library.  The framework
handles role separation (system / user / assistant), message serialisation,
and session state.  No tools registered — pure conversation.

### Level 4 — Pydantic AI ReAct with tools

Adds a ReAct (Reason + Act) loop.  The agent can call three tools:

| Tool | What it does |
|---|---|
| `fetch_web(url)` | Fetch a URL and return the text content (up to 8 000 chars) |
| `read_folder(path)` | List files in the project directory |
| `write_output(filename, content)` | Save a file to `./output/` |

Tool calls appear live in **yellow**, results in **dim yellow**, and the
final answer streams in **magenta**.

### Level 5 — Google ADK multi-agent

Uses [Google ADK](https://google.github.io/adk-docs/) with a LiteLlm backend.
A root orchestrator delegates work to two specialised sub-agents:

| Sub-agent | Tools | Role |
|---|---|---|
| `web_agent` | `web_fetch` | Fetch URLs and summarise content |
| `file_agent` | `list_project_files`, `save_output_file` | Read project files, write to `./output/` |

ADK manages routing, session state, and the sub-agent lifecycle.

---

## Slash commands

Available in every level:

| Command | Description |
|---|---|
| `/switch [1-5]` | Switch to another level (blank = list all) |
| `/provider [name]` | Change API provider (blank = list available) |
| `/model [name]` | Change model (blank = list available) |
| `/clear` | Reset conversation history |
| `/exit` | Return to the main menu |
| `/help` | Show command reference |

---

## Models

| Model ID | Provider(s) | Notes |
|---|---|---|
| `deepseek/deepseek-r1` | OpenRouter | Reasoning model — shows `⟨thinking⟩` steps |
| `anthropic/claude-haiku-4.5` | OpenRouter, Anthropic | Fast and efficient |
| `openai/gpt-4o-mini` | OpenRouter, OpenAI | Lightweight GPT |
| `openai/gpt-4o` | OpenRouter, OpenAI | Full GPT flagship |
| `ibm-granite/granite-4.1-8b` | OpenRouter | Open-weight model |

---

## Terminal colours

| Colour | Meaning |
|---|---|
| Cyan | Level 1 LLM response |
| Blue | Level 2 Chat response |
| Green | Level 3 Chat Assistant response |
| Magenta | Level 4 Tool Assistant final answer |
| Yellow | Level 5 Agent response · tool calls in all levels |
| Dim italic | DeepSeek R1 reasoning tokens `⟨thinking⟩…⟨/thinking⟩` |
| Dim yellow | Tool return values |
| Red | Errors |

---

## Environment variables

| Variable | Provider |
|---|---|
| `OPENROUTER_API_KEY` | OpenRouter (recommended — unlocks all 5 models) |
| `OPENAI_API_KEY` | OpenAI direct API |
| `ANTHROPIC_API_KEY` | Anthropic direct API |

The provider is auto-detected in priority order: OpenRouter → OpenAI → Anthropic.
You can override it at runtime with `/provider <name>`.

---

## Project structure

```
learn-agent/
├── main.py           launcher — level menu, subprocess loop
├── config.py         shared state, model catalog, HTTP helpers, slash commands
├── requirements.txt
├── level1.py         Level 1 — direct HTTP, stateless
├── level2.py         Level 2 — direct HTTP, full context
├── level3.py         Level 3 — Pydantic AI chat
├── level4.py         Level 4 — Pydantic AI ReAct + tools
├── level5/
│   ├── __init__.py
│   └── agent.py      Level 5 — Google ADK multi-agent
└── output/           files written by levels 4 and 5
```

---

## Dependency notes

- **`anthropic`** is pinned to `>=0.72.0,<0.100.0`.
  Pydantic AI 0.8.x imports `UserLocation` from the Anthropic beta types, a
  symbol that was removed in anthropic SDK 0.100+.  This pin will be lifted
  once pydantic-ai ships a compatible release.

- **`litellm`** is required for the Google ADK LiteLlm backend used in Level 5.

- Python **3.9+** is supported for levels 1–4.  Google ADK emits warnings on
  Python 3.9 (end-of-life); upgrading to 3.10+ silences them and enables MCP
  support in ADK.
