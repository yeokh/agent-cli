# Pi Sub-Agent Demonstration

Sub-agents are isolated `pi` processes spawned from within a parent agent session. Each sub-agent has its own context window, system prompt, model, and tools.

## What Are Sub-Agents?

- **Isolation**: Each subagent runs in a separate process with fresh context
- **Specialization**: Different agents optimized for specific tasks (scout, planner, reviewer, etc.)
- **Composition**: Single agents, parallel execution, or sequential chains with context passing
- **Streaming**: Real-time output and tool call visibility

## Three Execution Modes

### 1. Single Agent
One agent processes one task:
```
{ agent: "scout", task: "Find all auth middleware" }
```

### 2. Parallel Execution
Multiple agents run concurrently (max 8 tasks, 4 concurrent):
```
{ tasks: [
  { agent: "scout", task: "Find auth code" },
  { agent: "scout", task: "Find model definitions" }
]}
```

### 3. Chain (Sequential with Context Passing)
Tasks execute sequentially, with `{previous}` placeholder:
```
{ chain: [
  { agent: "scout", task: "Find all database calls in auth.ts" },
  { agent: "planner", task: "Create optimization plan for {previous}" },
  { agent: "worker", task: "Implement the plan from {previous}" }
]}
```

## Agent Definition Format

Agent files are Markdown with YAML frontmatter:

```markdown
---
name: scout
description: Fast codebase reconnaissance
tools: read, grep, find, ls, bash
model: claude-haiku-4-5
---

You are a scout. Quickly investigate a codebase...
(system prompt follows)
```

**Locations:**
- User agents: `~/.pi/agent/agents/*.md` (always loaded)
- Project agents: `.pi/agents/*.md` (requires `agentScope: "both"` or `"project"`)

## Standard Agent Library

| Agent | Purpose | Model | Tools |
|-------|---------|-------|-------|
| `scout` | Fast recon, compressed output | Haiku | read, grep, find, ls, bash |
| `planner` | Creates implementation plans | Sonnet | read, grep, find, ls |
| `reviewer` | Code review | Sonnet | read, grep, find, ls, bash |
| `worker` | General-purpose | Sonnet | all default (read, bash, edit, write) |

## Installation

Symlink the extension and agent definitions:

```bash
# Extension
mkdir -p ~/.pi/agent/extensions/subagent
ln -sf "$(pwd)/examples/extensions/subagent/index.ts" ~/.pi/agent/extensions/subagent/
ln -sf "$(pwd)/examples/extensions/subagent/agents.ts" ~/.pi/agent/extensions/subagent/

# Agents
mkdir -p ~/.pi/agent/agents
for f in examples/extensions/subagent/agents/*.md; do
  ln -sf "$(pwd)/$f" ~/.pi/agent/agents/$(basename "$f")
done

# Workflow prompts
mkdir -p ~/.pi/agent/prompts
for f in examples/extensions/subagent/prompts/*.md; do
  ln -sf "$(pwd)/$f" ~/.pi/agent/prompts/$(basename "$f")
done
```

## Interactive Examples

Once installed, open pi and try:

### Single Agent
```
Find all files that import the express module
```
→ Dispatches to scout agent (default)

### With Explicit Agent
```
Use scout to list all environment variable usage
```
→ "Use scout" → dispatches to scout tool

### Parallel Tasks
```
Run 2 scouts in parallel: one to find models, one to find providers
```

### Chained Workflow (via prompt template)
```
/implement add Redis caching to the session store
```
→ Executes: scout → planner → worker
→ Each step receives previous output via `{previous}` placeholder

```
/scout-and-plan refactor auth to support OAuth
```
→ Executes: scout → planner (no implementation)

```
/implement-and-review add input validation to API endpoints
```
→ Executes: worker → reviewer → worker

## SDK Usage Example

```typescript
import { createAgentSession } from "@earendil-works/pi-coding-agent";

const { session } = await createAgentSession();

// Single agent via subagent tool
await session.prompt(`
Use subagent tool:
{
  "agent": "scout",
  "task": "Find all database connection pooling code"
}
`);

// Parallel execution
await session.prompt(`
Use subagent tool with parallel tasks:
{
  "tasks": [
    { "agent": "scout", "task": "Find authentication code" },
    { "agent": "scout", "task": "Find API endpoint definitions" },
    { "agent": "scout", "task": "Find error handling patterns" }
  ]
}
`);

// Chain execution
await session.prompt(`
Use subagent tool with a chain:
{
  "chain": [
    { "agent": "scout", "task": "Find all middleware in src/middleware/" },
    { "agent": "planner", "task": "Plan refactoring for {previous}" },
    { "agent": "worker", "task": "Implement according to {previous}" }
  ]
}
`);
```

## Security & Project Agents

**Default behavior**: Only loads user-level agents from `~/.pi/agent/agents`

**To enable project-local agents:**
- Set `agentScope: "project"` or `"both"` in tool parameters
- Interactive mode prompts for confirmation on untrusted projects
- Trusted projects skip additional confirmation

**Why?**: Project agents (`.pi/agents/*.md`) are repo-controlled and can instruct the model to read files, run bash, etc.

## Output & Display

**Collapsed view** (default):
- Status icon (✓/✗/⏳) and agent name
- Last 10 items (tool calls and text)
- Usage stats: `turns ↑input ↓output RcacheRead WcacheWrite $cost ctx:tokens model`

**Expanded view** (Ctrl+O):
- Full task and output
- All tool calls with formatted arguments
- Final output rendered as Markdown
- Per-task usage for chains/parallel

**Parallel streaming**:
- Live status updates as tasks complete
- Shows "2/3 done, 1 running"
- Each task output capped at 50 KB (full results in details)

## Error Handling

- **Exit code != 0**: Returns stderr as error message
- **stopReason "error"**: LLM error propagated
- **stopReason "aborted"**: User aborted (Ctrl+C kills subprocess)
- **Chain mode**: Stops at first failure, reports which step

## Practical Workflows

### Rapid Feature Investigation
```
scout → find related code
↓ (via {previous})
planner → suggest implementation
↓ (via {previous})
worker → code it
```

### Code Review Pipeline
```
worker → implement feature
↓
reviewer → review against standards
↓
worker → incorporate feedback
```

### Parallel Recon
```
scout-1: Find database code
scout-2: Find caching code
scout-3: Find performance metrics
(all return compressed summaries for worker to synthesize)
```

## Limitations

- Max 8 parallel tasks (4 concurrent by default)
- Parallel output capped at 50 KB per task (full results in details)
- Agents discovered fresh on each invocation (allows editing mid-session)
- Can only pass text between chain steps via `{previous}`
