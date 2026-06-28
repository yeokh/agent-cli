# Workshop: Engineering an AI Agent with Claude Agent SDK

Welcome! In this workshop you will explore, extend, and customize the Claude Agent
to understand how production file-processing AI agents are built and controlled
using the **Claude Agent SDK** for Python.

---

## Prerequisites

1. Complete the [quick-start](../README.md#quick-start) and verify the agent runs
   end-to-end (click **Run Agent** and see output in the outbox) before starting.
2. Have at least one API key set (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or
   `OPENROUTER_API_KEY`). OpenAI/OpenRouter also require `GATEWAY_URL`.
3. Basic Python familiarity — you will read and edit `.py` files.

---

## Learning objectives

By the end of this workshop you will be able to:

1. Explain the **Claude Agent SDK loop** and how `query()` differs from a single LLM API call
2. Understand Claude Agent SDK **hooks** and how they intercept tool calls
3. Trace the three event types in the log stream: `[assistant]`, `[tool_use]`, `[result]`
4. Write `instruction.md` files that produce reliable, deterministic agent behavior
5. Add new **custom tools** via an MCP server (and explain when to use built-ins)
6. Implement a **guardrail** that validates `instruction.md` before the agent runs
7. Build **domain-specific tool modules** and load them conditionally
8. Chain multiple Claude Agent SDK calls into a **multi-stage processing pipeline**

---

## Claude Agent SDK — core concepts

### Single LLM call vs. Claude agentic loop

```
Single LLM call:
  prompt → LLM → response            (one round trip, no tools)

Claude Agent SDK loop (query()):
  prompt → LLM → tool call → tool result → LLM → tool call → … → final answer
                 ↑_________________________________↑
                 (repeated automatically until task is complete)
```

### Hooks

Claude Agent SDK lets you hook into tool execution without building your own
tool framework. Hooks can log, block, or modify tool calls:

```python
from claude_agent_sdk import HookMatcher, ClaudeAgentOptions

async def pre_tool_use(input_data, tool_use_id, context):
    if input_data["tool_name"] == "Write":
        return {"hookSpecificOutput": {"permissionDecision": "allow"}}
    return {}

options = ClaudeAgentOptions(
    hooks={"PreToolUse": [HookMatcher(hooks=[pre_tool_use])]}
)
```

### Streaming events

The harness uses `include_partial_messages=True` to stream text deltas. Each
line is logged as:

| Log prefix | Source | Meaning |
|------------|--------|---------|
| `[assistant]` | streaming text delta | Model output |
| `[tool_use]` | hook in `PreToolUse` | Model invoked a tool |
| `[result]` | hook in `PostToolUse` | Tool result returned |

---

## Track overview

### Beginner track  *(~60 min)*

| Exercise | Topic |
|----------|-------|
| [01 — Explore](beginner/01_explore.md) | Run the agent, trace execution, understand SDK events |
| [02 — Modify Instructions](beginner/02_modify_instructions.md) | Change `instruction.md`; observe different outputs and model behaviors |
| [03 — Add a Custom Tool](beginner/03_add_tool.md) | Add an MCP tool and expose it to the agent |

### Advanced track  *(~90 min)*

| Exercise | Topic |
|----------|-------|
| [04 — Guardrail Check](advanced/04_guardrail.md) | Pre-flight safety validation before the main agent runs |
| [05 — Custom Toolsets](advanced/05_custom_toolsets.md) | Organize tools into domain modules; load them conditionally |
| [06 — Multi-Agent Pipeline](advanced/06_multi_agent.md) | Chain agent runs; build a two-stage extract → analyze pipeline |

---

## How to work through the exercises

1. Read the **Objective** and **Background** sections first.
2. Follow the numbered **Steps** — code snippets are provided for every change.
3. After each step, click **Run Agent** in the web UI and verify the change worked
   by checking the log stream and the outbox.
4. Answer the **Reflection** questions at the end of each exercise before moving on.

---

## Key files to keep open

| File | Role |
|------|------|
| `claude_agent.py` | Agent logic — model registry, hooks, Claude Agent SDK configuration |
| `web_app.py`      | Web layer — Flask endpoints, SSE streaming, inbox editor |
| `inbox/instruction.md` | Task definition — what the agent does this run (editable in browser) |
| Browser terminal  | Live event stream — what the agent is doing right now |

---

## Getting help

- Re-read [README.md](../README.md) for architecture details.
- Check the [Claude Agent SDK docs](https://code.claude.com/docs/en/agent-sdk/overview) for API reference.
- Browse the [Claude Agent SDK Python reference](https://code.claude.com/docs/en/agent-sdk/python.md) for details.
- Look for `# WORKSHOP` comments in `claude_agent.py` and `web_app.py` — each
  comment points to the relevant exercise and explains what to change.
- Ask the instructor!
