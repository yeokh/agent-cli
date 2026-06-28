# Exercise 01 — Explore the Claude Agent

**Track:** Beginner | **Time:** ~20 min

---

## Objective

Run the agent for the first time and build a mental model of how the
**Claude Agent SDK loop** works by tracing execution from the browser through
`web_app.py`, into `claude_agent.py`, and out to the LLM provider.

---

## Background

### Single LLM call vs. Claude Agent SDK loop

```
Single LLM call:
  prompt → LLM → response            (one round trip, no tools)

Claude Agent SDK loop:
  prompt → LLM → tool call → tool result → LLM → tool call → … → final answer
                 ↑_________________________________↑
                 (SDK handles this loop automatically)
```

The Claude Agent SDK manages this loop automatically. Your code supplies:
1. A **model** — passed in `ClaudeAgentOptions(model=...)`
2. A **system prompt** — standing instructions baked into every LLM call
3. **Built-in tools** — Read/Write/Edit/Glob/Grep/Bash
4. A **task prompt** — the specific job for this run (read from `instruction.md`)

### Log event types

| Log prefix | Source | Meaning |
|------------|--------|---------|
| `[assistant]` | streaming text delta | Model output |
| `[tool_use]` | `PreToolUse` hook | Model invoked a tool |
| `[result]` | `PostToolUse` hook | Tool returned a result |

### Tools available in this harness

| Tool | What it does |
|------|-------------|
| `Read` | Read a file |
| `Write` | Write a file |
| `Edit` | Update part of a file |
| `Glob` | Find files by pattern |
| `Grep` | Search file contents |
| `Bash` | Execute a shell command |

---

## Steps

### 1. Start the web UI

```bash
cd claude-agent
export ANTHROPIC_API_KEY=<redacted-anthropic-api-key>   # or OPENAI_API_KEY / OPENROUTER_API_KEY
python web_app.py
```

Open **http://localhost:8080** in your browser.

### 2. Inspect the inbox

Click each file in the **Inbox** panel:
- `instruction.md` — the task the agent will follow; read it now
- `playbook-w-vul-1.yaml`, `playbook-w-vul-2.yaml` — intentionally vulnerable playbooks
- `playbook-wo-vul-1.yaml` — a safer example

**New feature**: click the **✏ Edit** button in the viewer toolbar to edit
any inbox file directly in your browser. Click **💾 Save** to write the change back.
This is how you modify `instruction.md` without leaving the browser.

### 3. Select a model

In the bottom-right dropdown, pick any available model. The list is
built from whichever API keys are present in your environment — models whose
key is missing do not appear. OpenAI/OpenRouter models require `GATEWAY_URL`.

### 4. Run the agent

Click **Run Agent**. Watch the log stream in the terminal panel below.

### 5. Identify event types in the log

As the agent runs, find examples of each event type:

```
[assistant] I'll start by reading instruction.md…
[tool_use] Read(file_path='inbox/instruction.md')
[result] Read: "This document provides instructions…"
[tool_use] Glob(pattern='**/*.yaml', path='/.../inbox')
[result] Glob: ["playbook-w-vul-1.yaml", ...]
[tool_use] Write(file_path='outbox/result.log', ...)
[result] Write: {"written": true}
```

Count how many tool calls the agent makes in total. Each one is a round
trip to the LLM and back.

### 6. Inspect the output

After the run completes, click the files in the **Outbox** panel. Check:
- `result.log` — the JSON output you asked for
- `agent.log` — the full run log, written by `_agent_thread()` in `web_app.py`

### 7. Trace the code

Open `claude_agent.py` and `web_app.py` side by side. Find each landmark:

| Thing to find | Where |
|---------------|-------|
| The model registry | `_registry()` in `claude_agent.py` |
| How available models are filtered | `get_available_models()` in `claude_agent.py` |
| How SDK options are built | `_build_sdk_options()` in `claude_agent.py` |
| The agent's standing instructions | `_SYSTEM_PROMPT` in `claude_agent.py` |
| Tool logging hooks | `pre_tool_use()` and `post_tool_use()` |
| Where streaming is handled | `_run_agent_async()` in `claude_agent.py` |
| How the background thread is started | `api_run_agent()` in `web_app.py` |
| Where logs flow from thread to browser | `_agent_thread()` → `AgentState.add_log()` → `api_agent_logs()` |

### 8. Understand the thread model

```
Browser tab
    │  GET /api/agent/logs (long-lived SSE connection)
    ▼
Flask request thread (api_agent_logs)
    │  reads AgentState.snapshot() every 0.4 s
    │
AgentState (shared object with threading.Lock)
    │
Background thread (_agent_thread)
    │  calls claude_agent.run_agent()  →  Claude Agent SDK loop  →  LLM provider
    └─ calls state.add_log() for every event line
```

Why a background thread? `query()` blocks until the agentic loop finishes — which
can take minutes. The thread lets the agent run while the SSE connection streams
its output live.

---

## Reflection questions

1. The `_SYSTEM_PROMPT` in `claude_agent.py` is fixed — it never changes between
   runs. The task-specific instructions live in `instruction.md` and are read
   by the agent at runtime. What are the security implications of this split?

2. The `Bash` tool can execute shell commands on the host. What could a malicious
   `instruction.md` do with this, even with hooks in place?

3. The SDK uses a streaming message loop rather than an explicit event stream.
   Why do we log tool use via hooks instead?

4. Click **Run Agent** a second time without clearing the outbox. What happens?
   Does the agent overwrite, append to, or skip the existing files?

5. Change the model in the dropdown and run again. Does the output differ?
   Which model is faster? Which produces better prose?

---

## Key takeaways

- The Claude Agent SDK loop is automatic: `query()` manages the tool-calling cycle.
- Every agent action appears in the log as `[tool_use]`, `[result]`, or
  `[assistant]` events — you can follow exactly what the agent did and why.
- `web_app.py` is a thin web layer; all agent logic lives in `claude_agent.py`.
- `instruction.md` controls *what* the agent does; `_SYSTEM_PROMPT` controls
  *how* it behaves (its constraints and conventions).
- Hooks are the bridge between SDK tool calls and the UI log stream.
- The inbox file editor lets you iterate on `instruction.md` without leaving the browser.
