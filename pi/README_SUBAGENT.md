# Pi Sub-Agent Complete Documentation

## Documentation Files

This directory contains comprehensive sub-agent documentation and examples:

### Quick Reference
- **[SUBAGENT_SUMMARY.txt](./SUBAGENT_SUMMARY.txt)** - One-page quick reference with all essentials
- **[SUBAGENT_VISUALS.txt](./SUBAGENT_VISUALS.txt)** - Visual diagrams and execution models

### Detailed Guides
- **[subagent-demo.md](./subagent-demo.md)** - Concepts, installation, standard agents
- **[subagent-workflow-example.md](./subagent-workflow-example.md)** - 5 real-world workflow examples
- **[subagent-api-reference.md](./subagent-api-reference.md)** - Complete API documentation

### Code Examples
- **[subagent-interactive-demo.ts](./subagent-interactive-demo.ts)** - Runnable TypeScript demo

---

## Quick Start

### Installation
```bash
# Extension
mkdir -p ~/.pi/agent/extensions/subagent
ln -sf $(pwd)/examples/extensions/subagent/index.ts ~/.pi/agent/extensions/subagent/
ln -sf $(pwd)/examples/extensions/subagent/agents.ts ~/.pi/agent/extensions/subagent/

# Agents  
mkdir -p ~/.pi/agent/agents
for f in examples/extensions/subagent/agents/*.md; do
  ln -sf $(pwd)/$f ~/.pi/agent/agents/$(basename "$f")
done

# Workflow prompts
mkdir -p ~/.pi/agent/prompts
for f in examples/extensions/subagent/prompts/*.md; do
  ln -sf $(pwd)/$f ~/.pi/agent/prompts/$(basename "$f")
done
```

### Interactive Usage
```bash
pi
> /implement add database connection pooling
> Use scout to find all error handling patterns
> Run 3 scouts in parallel: auth, models, providers
```

---

## Three Execution Modes

### 1. Single Agent
One agent processes one task.
```json
{
  "agent": "scout",
  "task": "Find all authentication code"
}
```

### 2. Parallel Execution
Multiple agents run concurrently (max 8, 4 concurrent).
```json
{
  "tasks": [
    { "agent": "scout", "task": "Find models" },
    { "agent": "scout", "task": "Find providers" },
    { "agent": "scout", "task": "Find middleware" }
  ]
}
```

### 3. Chain Execution
Sequential tasks with `{previous}` context passing.
```json
{
  "chain": [
    { "agent": "scout", "task": "Find caching code" },
    { "agent": "planner", "task": "Plan refactoring for {previous}" },
    { "agent": "worker", "task": "Implement according to {previous}" }
  ]
}
```

---

## Standard Agents

| Agent | Purpose | Model | Tools |
|-------|---------|-------|-------|
| **scout** | Fast codebase reconnaissance | claude-haiku-4-5 | read, grep, find, ls, bash |
| **planner** | Creates implementation plans | claude-sonnet-4-5 | read, grep, find, ls |
| **reviewer** | Code review and feedback | claude-sonnet-4-5 | read, grep, find, ls, bash |
| **worker** | General-purpose implementation | claude-sonnet-4-5 | read, bash, edit, write |

---

## Workflow Templates

Available as `/command` shortcuts:

### /implement <query>
Executes: scout → planner → worker

Use for: Full feature implementation from research to code

### /scout-and-plan <query>
Executes: scout → planner

Use for: Analysis and planning without implementation

### /implement-and-review <query>
Executes: worker → reviewer → worker

Use for: Implementation with review feedback iteration

---

## Real-World Examples

### Feature Implementation
```
Scout finds caching patterns
  ↓
Planner creates Redis integration plan
  ↓
Worker implements Redis caching
  ↓
Reviewer checks for issues
  ↓
Worker refines based on feedback
```

### Parallel Analysis
```
Scout-1: Auth code          ⏳ running
Scout-2: Models             ⏳ running
Scout-3: Middleware         ⏳ running
       (all concurrent)
  ↓
Worker synthesizes findings
```

### Multi-angle Review
```
Reviewer (security)         ⏳ running
Reviewer (performance)      ⏳ running
Reviewer (architecture)     ⏳ running
       (all concurrent)
  ↓
Worker prioritizes fixes
```

---

## Key Concepts

### Isolation
Each subagent runs in a separate subprocess with:
- Fresh context window
- Isolated model and tools
- Separate working directory (if specified)
- Real-time streaming output

### Specialization
Different agents for different tasks:
- **Scout**: Fast, cheap, reconnaissance-focused
- **Planner**: Medium-cost, strategic planning
- **Reviewer**: Medium-cost, quality assessment
- **Worker**: Full-featured, general-purpose

### Context Passing
In chain mode, `{previous}` is replaced with previous step's output:
```
Step 1: "Find auth code" → "File A has JWT, File B has OAuth"
Step 2: "Plan refactoring for {previous}" → "Plan refactoring for File A has JWT, File B has OAuth"
```

### Streaming Output
All modes show:
- Real-time tool calls and execution
- Status updates (✓/✗/⏳)
- Usage stats (tokens, cost, cache)
- Markdown-rendered output

### Error Handling
- Chain stops at first failure with error message
- Includes failed step number and diagnostics
- User abort (Ctrl+C) propagates to subprocess
- Full error messages captured in tool details

---

## Display Modes

### Collapsed View (default)
- Status icon and agent name
- Last 10 display items
- One-line usage stats
- Hint: "Ctrl+O to expand"

### Expanded View (Ctrl+O)
- Full task description
- All tool calls formatted
- Final output as Markdown
- Per-task usage (chain/parallel)
- Aggregate totals

---

## API Parameters

### Common
```typescript
agent: string              // Agent name (single mode)
task: string               // Task description
tasks: Array<...>          // Parallel tasks
chain: Array<...>          // Chain steps
agentScope?: "user" | "project" | "both"  // Default: "user"
confirmProjectAgents?: boolean             // Default: true
cwd?: string               // Working directory
```

### Single Mode
```json
{
  "agent": "scout",
  "task": "Find express imports"
}
```

### Parallel Mode
```json
{
  "tasks": [
    { "agent": "scout", "task": "..." },
    { "agent": "scout", "task": "..." }
  ]
}
```

### Chain Mode
```json
{
  "chain": [
    { "agent": "scout", "task": "Find code" },
    { "agent": "planner", "task": "Plan based on {previous}" }
  ]
}
```

---

## Security

### Default Behavior
- Loads user agents only: `~/.pi/agent/agents/*.md`
- Safe and controlled

### Project Agents
- Located in: `.pi/agents/*.md`
- Repository-controlled (can execute bash/file ops)
- Requires: `agentScope: "project"` or `"both"`
- Interactive: Prompts on untrusted projects
- SDK: No auto-prompt

### Best Practices
- Keep project agents in trusted repos only
- Review agent definitions before using `agentScope: "both"`
- Use default `agentScope: "user"` for untrusted code

---

## Limitations

- **Max parallel tasks**: 8
- **Max concurrent**: 4 (others queue)
- **Output cap (parallel)**: 50 KB per task
- **Full results**: Always in tool details (not truncated)
- **Agent discovery**: Fresh on each invocation
- **Context passing**: Text only via `{previous}`
- **Chain behavior**: Stops on first error

---

## Usage Statistics

Each result includes:
- **turns**: Number of LLM turns
- **↑input**: Input tokens
- **↓output**: Output tokens
- **RcacheRead**: Cache read tokens (if any)
- **WcacheWrite**: Cache write tokens (if any)
- **$cost**: Monetary cost
- **ctx:tokens**: Total context used
- **model**: Model name

Example: `3 turns ↑1.2k ↓2.1k $0.0156 ctx:4.3k claude-sonnet-4-5`

---

## Troubleshooting

### Agent Not Found
```
"Unknown agent: \"name\". Available agents: scout, planner, reviewer, worker"
```
Check agent name spelling and verify installation.

### Project Agents Not Loading
```
Set agentScope: "project" or "both" to use .pi/agents/
```
Project agents require explicit scope setting.

### Chain Stopped Early
```
"Chain stopped at step 2 (planner): ..."
```
Previous step failed. Check the error message and step details.

### High Token Usage
Scout is faster/cheaper. Consider:
1. Use scout for initial exploration
2. Pass compressed output to worker
3. Use specific file/directory when possible

---

## Document Navigation

```
SUBAGENT_SUMMARY.txt          ← Start here (quick reference)
    ↓
SUBAGENT_VISUALS.txt          ← Understand execution models
    ↓
subagent-demo.md              ← Learn concepts and installation
    ↓
subagent-workflow-example.md  ← See real-world examples
    ↓
subagent-api-reference.md     ← Deep API documentation
    ↓
subagent-interactive-demo.ts  ← Run code examples
```

---

## SDK Integration

```typescript
import { createAgentSession } from "@earendil-works/pi-coding-agent";

const { session } = await createAgentSession();

// Single agent
await session.prompt(`
Use subagent: agent=scout, task="Find auth code"
`);

// Chain
await session.prompt(`
Use subagent with chain:
1. scout: "Find database code"
2. planner: "Plan optimization for {previous}"
3. worker: "Implement optimization: {previous}"
`);

// Parallel
await session.prompt(`
Use subagent parallel tasks:
1. scout: "Find auth"
2. scout: "Find models"
3. scout: "Find providers"
`);
```

---

## Advanced Customization

Create project-specific agents in `.pi/agents/`:

```markdown
---
name: database-expert
description: Specialized database optimization
tools: read, grep, find, ls, bash
model: claude-opus-4-5
---

You are a database expert specialized in:
- Schema design and normalization
- Query optimization
- Index strategies
```

Use with `agentScope: "both"`:
```json
{
  "agentScope": "both",
  "chain": [
    { "agent": "scout", "task": "Analyze database" },
    { "agent": "database-expert", "task": "Optimize based on {previous}" }
  ]
}
```

---

## Support & More Info

For complete details, see:
- [subagent-demo.md](./subagent-demo.md) - Concepts and installation
- [subagent-api-reference.md](./subagent-api-reference.md) - Full API docs
- [subagent-workflow-example.md](./subagent-workflow-example.md) - 5 detailed workflows

