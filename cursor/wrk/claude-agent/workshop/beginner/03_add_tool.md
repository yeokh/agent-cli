# Exercise 03 — Add a Custom Tool

**Track:** Beginner | **Time:** ~20 min

---

## Objective

Extend the agent's capabilities by adding a custom tool via an **in-process MCP
server** and exposing it to the Claude Agent SDK. You will add a `word_count`
tool that returns line/word/character counts for a file.

---

## Background

Claude Agent SDK ships with built-in tools (Read/Write/Edit/Glob/Grep/Bash). For
domain-specific logic, you can add your own tools using the SDK's MCP helper:

```python
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool("word_count", "Count words in a file", {"file_path": str})
async def word_count(args):
    return {"content": [{"type": "text", "text": "..." }]}

server = create_sdk_mcp_server(name="custom", tools=[word_count])
```

The tool is then exposed as `mcp__custom__word_count` and can be listed in
`allowed_tools` to auto-approve it.

---

## Steps

### 1. Add the tool definition

Open `claude_agent.py` and add the following near the top of the file (below
the imports):

```python
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool("word_count", "Count lines, words, and characters in a text file", {"file_path": str})
async def word_count(args):
    file_path = args.get("file_path", "")
    try:
        text = Path(file_path).read_text(encoding="utf-8")
        lines = text.count("\\n")
        words = len(text.split())
        chars = len(text)
        return {"content": [{"type": "text", "text": f"{lines} lines, {words} words, {chars} chars"}]}
    except Exception as exc:
        return {"content": [{"type": "text", "text": f"Error: {exc}"}]}

CUSTOM_TOOLS = create_sdk_mcp_server(name="custom", tools=[word_count])
```

### 2. Register the MCP server

In `_build_sdk_options()` in `claude_agent.py`, extend the `ClaudeAgentOptions`
to include the MCP server and allow the tool:

```python
options = ClaudeAgentOptions(
    ...
    mcp_servers={"custom": CUSTOM_TOOLS},
    allowed_tools=[..., "mcp__custom__word_count"],
)
```

Restart `web_app.py` after the change.

### 3. Write an instruction that uses the tool

Use the browser editor to replace `inbox/instruction.md` with:

```markdown
# Task: File Statistics

For each .yaml file in the inbox:
1. Use the word_count tool to get its size statistics.
2. Read the file content.

Then write `outbox/file_stats.md` with a Markdown table:

| Filename | Lines | Words | Characters |
|----------|-------|-------|------------|
| ...      | ...   | ...   | ...        |

Sort rows alphabetically by filename.
```

### 4. Run the agent

Click **Run Agent** and watch for log lines like:

```
[tool_use] mcp__custom__word_count(file_path='inbox/playbook-w-vul-1.yaml')
[result] mcp__custom__word_count: 21 lines, 120 words, 812 chars
```

Check `outbox/file_stats.md` in the Outbox panel.

---

## Reflection questions

1. Why is a custom tool better than asking the model to estimate counts?
2. What happens if your tool reads a file outside the inbox? How would you
   guard against that in the tool implementation?
3. If your tool returns a large string (100 KB), how does the agent behave?

---

## Key takeaways

- Built-in tools cover common file and shell needs, but custom MCP tools let
  you add domain-specific capabilities safely.
- MCP tools are exposed as `mcp__server__tool` names in `allowed_tools`.
- Custom tools are just async Python functions returning MCP content blocks.
