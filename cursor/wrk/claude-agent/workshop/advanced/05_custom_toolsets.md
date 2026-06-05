# Exercise 05 — Build Custom Toolsets

**Track:** Advanced | **Time:** ~30 min

---

## Objective

Organize related tool functions into domain-specific Python modules, load them
as MCP servers in `claude_agent.py`, and understand when to use modules vs.
inline tool definitions.

---

## Background

### The toolset problem

As you add more tools in Exercise 03, `claude_agent.py` grows long. When tools
share helper logic (CSV parsing, report formatting), duplicating them inline
becomes a maintenance problem.

The solution is to group related tools into **toolset modules** — plain Python
files in a `tools/` directory. Each module exports a MCP server created with
`create_sdk_mcp_server()`. `claude_agent.py` imports and combines them.

---

## Steps

### 1. Create the tools directory

```bash
mkdir -p tools
touch tools/__init__.py
```

### 2. Write a CSV toolset module

Create `tools/csv_tools.py`:

```python
"""
CSV Toolset for Claude Agent
────────────────────────────
Domain-specific tools for reading and transforming CSV files.
"""

import csv
import json
from pathlib import Path
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool


@tool("csv_schema", "Return the column names and row count of a CSV file", {"file_path": str})
async def csv_schema(args: dict[str, Any]):
    file_path = Path(args["file_path"])
    with file_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        rows = sum(1 for _ in reader)
    text = f"Columns: {', '.join(columns)}\\nRows: {rows}"
    return {"content": [{"type": "text", "text": text}]}


@tool("csv_to_json", "Parse a CSV file and return all rows as JSON", {"file_path": str})
async def csv_to_json(args: dict[str, Any]):
    file_path = Path(args["file_path"])
    with file_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {"content": [{"type": "text", "text": json.dumps(rows, indent=2)}]}


CSV_TOOLS = create_sdk_mcp_server(name="csv", tools=[csv_schema, csv_to_json])
```

### 3. Load the toolset in `claude_agent.py`

In `claude_agent.py`, import and register the MCP server:

```python
from tools.csv_tools import CSV_TOOLS

options = ClaudeAgentOptions(
    ...
    mcp_servers={"csv": CSV_TOOLS},
    allowed_tools=[..., "mcp__csv__csv_schema", "mcp__csv__csv_to_json"],
)
```

### 4. Write an instruction that uses the new tools

```markdown
# Task: CSV Analysis with Custom Tools

Read sample_data.csv from the inbox.

Step 1: Use csv_schema to understand the structure.
Step 2: Use csv_to_json to load the data.
Step 3: Write a Markdown report to `outbox/report.md` with:
  ## Executive Summary
  ## Findings (include the column list)
  ## Conclusion
```

Restart `web_app.py` and click **Run Agent**. Watch for `[tool_use]` lines
using `mcp__csv__csv_schema`, etc. in the log stream.

---

## Reflection questions

1. Why is a module-based toolset easier to maintain than a single monolithic
   `claude_agent.py` file?
2. How would you restrict these tools to only operate on files under `inbox/`?
3. What happens if your MCP server raises an exception? How is it logged?

---

## Key takeaways

- Use MCP tool servers to add domain-specific capabilities to the Claude Agent SDK.
- Group related tools into modules to keep `claude_agent.py` readable.
- Tool names are namespaced by server: `mcp__server__tool`.
