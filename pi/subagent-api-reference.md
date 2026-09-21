# Sub-Agent Tool API Reference

## Tool Name
`subagent`

## Parameters

All modes accept these common parameters:

```typescript
{
  agentScope?: "user" | "project" | "both"    // Default: "user"
  confirmProjectAgents?: boolean               // Default: true
  cwd?: string                                 // Working directory (single mode only)
}
```

### Mode 1: Single Agent

Execute one task with one agent.

```typescript
{
  agent: string        // Agent name (required for this mode)
  task: string         // Task description (required for this mode)
  cwd?: string         // Optional working directory
}
```

**Example**:
```json
{
  "agent": "scout",
  "task": "Find all TypeScript files that import the 'express' package"
}
```

### Mode 2: Parallel Execution

Execute multiple tasks concurrently.

```typescript
{
  tasks: Array<{
    agent: string      // Agent name
    task: string       // Task description
    cwd?: string       // Optional working directory
  }>
}
```

**Limits**:
- Max 8 tasks total
- Max 4 concurrent (others queue)
- Each task output capped at 50 KB (full results in tool details)

**Example**:
```json
{
  "tasks": [
    {
      "agent": "scout",
      "task": "Find all authentication-related code"
    },
    {
      "agent": "scout",
      "task": "Find all database query code"
    },
    {
      "agent": "scout",
      "task": "Find all error handling code"
    }
  ]
}
```

### Mode 3: Chain Execution

Execute tasks sequentially with context passing via `{previous}` placeholder.

```typescript
{
  chain: Array<{
    agent: string      // Agent name
    task: string       // Task with optional {previous} placeholder
    cwd?: string       // Optional working directory
  }>
}
```

**Behavior**:
- Tasks execute in order
- `{previous}` replaced with previous step's output
- Stops on first failure (returns error with failed step number)
- All previous results included in error response

**Example**:
```json
{
  "chain": [
    {
      "agent": "scout",
      "task": "Find all middleware implementations. List file paths and middleware names."
    },
    {
      "agent": "planner",
      "task": "Based on these middleware implementations: {previous}\n\nCreate a plan to consolidate and standardize them."
    },
    {
      "agent": "worker",
      "task": "Implement the consolidation plan: {previous}"
    }
  ]
}
```

## Common Parameters

### agentScope
Controls which agent directories are used:
- `"user"` (default): Load from `~/.pi/agent/agents/*.md` only
- `"project"`: Load from `.pi/agents/*.md` only  
- `"both"`: Load both, with project agents overriding user agents by name

**Security note**: Project agents are repository-controlled and can execute bash/file operations. Set to `"project"` or `"both"` only for trusted repositories.

### confirmProjectAgents
Whether to prompt before running project-local agents (only in interactive UI):
- `true` (default): Show confirmation dialog
- `false`: Skip confirmation (must be set explicitly)

Only affects interactive mode. SDK code bypasses this.

### cwd
Working directory for the agent process:
- Single mode: Pass as top-level parameter
- Parallel/chain: Pass per-task

## Return Value

```typescript
interface SubagentResult {
  content: [{
    type: "text"
    text: string          // Final output from agent
  }]
  
  details: {
    mode: "single" | "parallel" | "chain"
    agentScope: AgentScope
    projectAgentsDir: string | null
    results: Array<{
      agent: string                        // Agent name used
      agentSource: "user" | "project" | "unknown"
      task: string                         // Original task
      exitCode: number                     // 0 = success, non-zero = failure
      messages: Message[]                  // Full LLM conversation
      stderr: string                       // Any stderr output
      usage: {
        input: number                      // Input tokens
        output: number                     // Output tokens
        cacheRead: number                  // Cache read tokens
        cacheWrite: number                 // Cache write tokens
        cost: number                       // Monetary cost
        contextTokens: number              // Total context used
        turns: number                      // Number of LLM turns
      }
      model?: string                       // Model used (if inherited from parent)
      stopReason?: string                  // "end" | "error" | "aborted"
      errorMessage?: string                // Error details if stopReason === "error"
      step?: number                        // Step number in chain (1-indexed)
    }>
  }
  
  isError?: boolean      // true if any task failed (chain/single mode)
}
```

## Available Agents

Standard agents in `~/.pi/agent/agents/`:

| Name | Description | Model | Tools | 
|------|-------------|-------|-------|
| `scout` | Fast codebase reconnaissance, returns compressed output | claude-haiku-4-5 | read, grep, find, ls, bash |
| `planner` | Creates implementation plans from scouted context | claude-sonnet-4-5 | read, grep, find, ls |
| `reviewer` | Code review and quality assessment | claude-sonnet-4-5 | read, grep, find, ls, bash |
| `worker` | General-purpose implementation and coding | claude-sonnet-4-5 | read, bash, edit, write |

## System Prompts

Each agent has a specialized system prompt:

### scout.md
- Investigates codebase quickly
- Outputs structured findings
- Returns compressed context for handoff
- Uses Haiku (fast, low cost)

### planner.md
- Creates implementation plans from scout findings
- Structures output for worker consumption
- Suggests architecture and migration steps
- Uses Sonnet

### reviewer.md
- Reviews code for issues
- Checks security, performance, architecture
- Suggests specific improvements
- Uses Sonnet

### worker.md
- General-purpose coding agent
- Implements features, fixes bugs, refactors
- Full access to all tools
- Uses Sonnet

## Error Handling

### Exit Code Errors
```
exitCode: 1
stopReason: "error"
errorMessage: "..." // stderr or output
```

### Chain Failure
First failing step stops the chain:
```
{
  isError: true,
  content: [{ type: "text", text: "Chain stopped at step 2 (planner): ..." }],
  details: {
    results: [
      { /* successful step 1 */ },
      { /* failed step 2 */ }
    ]
  }
}
```

### Abort (Ctrl+C)
```
exitCode: -1 (or 143)
stopReason: "aborted"
```

### Unknown Agent
```
exitCode: 1
stderr: "Unknown agent: \"name\". Available agents: ..."
```

## Display Modes

### Collapsed View (default)
Shows:
- Status icon (✓/✗/⏳)
- Agent name
- Last 10 display items (tool calls + text)
- Usage stats on one line
- Hint: "Ctrl+O to expand"

### Expanded View (Ctrl+O)
Shows:
- Full task description
- Complete tool call list with formatted arguments
- Final output rendered as Markdown
- Per-task usage (chains/parallel)
- Aggregate totals

### Tool Call Formatting
Tool calls displayed as:
- bash: `$ command...`
- read: `read ~/path:line-range`
- write: `write ~/path (N lines)`
- edit: `edit ~/path`
- grep: `grep /pattern/ in ~/path`
- find: `find pattern in ~/path`
- ls: `ls ~/path`

## Usage Stats

Each result includes:
- **turns**: Number of LLM turns (assistant messages)
- **↑input**: Input tokens (green/positive)
- **↓output**: Output tokens (blue/negative)
- **RcacheRead**: Cache read tokens (cyan, if > 0)
- **WcacheWrite**: Cache write tokens (yellow, if > 0)
- **$cost**: Monetary cost (if available)
- **ctx:contextTokens**: Total context tokens used
- **model**: Model used (if not inherited)

Example: `3 turns ↑1.2k ↓2.1k RcacheRead WcacheWrite $0.0156 ctx:4.3k claude-sonnet-4-5`

## Workflow Templates (Prompt Templates)

Available as `/command` shortcuts:

### /implement <query>
Chain: scout → planner → worker

Use when: You want full implementation from research to code

### /scout-and-plan <query>
Chain: scout → planner

Use when: You want analysis and planning but not implementation

### /implement-and-review <query>
Chain: worker → reviewer → worker

Use when: You want to implement and iterate with review feedback

## SDK Integration Example

```typescript
import { createAgentSession } from "@earendil-works/pi-coding-agent";

const { session } = await createAgentSession();

session.subscribe((event) => {
  if (event.type === "message_update" && event.assistantMessageEvent.type === "text_delta") {
    process.stdout.write(event.assistantMessageEvent.delta);
  }
  if (event.type === "tool_execution_start" && event.toolName === "subagent") {
    console.log("Subagent starting...");
  }
});

// Single agent
await session.prompt(`
Use the subagent tool with:
{
  "agent": "scout",
  "task": "Find all files that import modules from 'src/utils'"
}
`);

// Chain
await session.prompt(`
Use the subagent tool with chain:
{
  "chain": [
    {
      "agent": "scout",
      "task": "Find all API endpoint definitions"
    },
    {
      "agent": "planner",
      "task": "Based on: {previous}\\n\\nCreate a plan to add API versioning"
    },
    {
      "agent": "worker",
      "task": "Implement API versioning: {previous}"
    }
  ]
}
`);

// Parallel
await session.prompt(`
Use the subagent tool with parallel tasks:
{
  "tasks": [
    { "agent": "scout", "task": "Find all error types defined" },
    { "agent": "scout", "task": "Find all HTTP status codes used" },
    { "agent": "scout", "task": "Find all logging patterns" }
  ]
}
`);
```

## Limitations

- **Max parallel tasks**: 8
- **Max concurrent**: 4 (others queue)
- **Output cap (parallel)**: 50 KB per task (full results in details)
- **Discovery**: Agents loaded fresh on each invocation (allows editing mid-session)
- **Context passing**: Only text via `{previous}` placeholder
- **Chain behavior**: Stops on first error (doesn't continue to next step)
