# Sub-Agent Workflow Examples

## Example 1: Feature Implementation Workflow

**Goal**: Add Redis caching to the session store

**Workflow Steps**:

```
Scout (Haiku) → Find caching code
    ↓ {previous}
Planner (Sonnet) → Create implementation plan
    ↓ {previous}
Worker (Sonnet) → Write the code
    ↓
Reviewer (Sonnet) → Review and suggest improvements
    ↓ {previous}
Worker (Sonnet) → Incorporate feedback
```

**Interactive Prompt**:
```
/implement add Redis caching to the session store
```

**SDK Execution**:
```json
{
  "chain": [
    {
      "agent": "scout",
      "task": "Find all session storage code and caching patterns in the codebase. Report file paths and key functions."
    },
    {
      "agent": "planner",
      "task": "Based on these findings: {previous}\n\nCreate an implementation plan for adding Redis caching to the session store. Include architecture, required dependencies, and migration steps."
    },
    {
      "agent": "worker",
      "task": "Based on this plan: {previous}\n\nImplement Redis caching for the session store. Write production-ready code with error handling."
    },
    {
      "agent": "reviewer",
      "task": "Review the implementation from the worker. Check for:\n- Error handling\n- Memory leaks\n- Redis connection pooling\n- Fallback behavior"
    },
    {
      "agent": "worker",
      "task": "Based on the reviewer's feedback: {previous}\n\nUpdate the implementation to address all concerns."
    }
  ]
}
```

**Output at Each Step**:
1. **Scout**: List of files, line ranges, key function signatures
2. **Planner**: Structured implementation plan (architecture, steps, dependencies)
3. **Worker**: Working code implementation
4. **Reviewer**: Issues found, improvement suggestions
5. **Worker (2nd pass)**: Updated code addressing all feedback

---

## Example 2: Parallel Codebase Analysis

**Goal**: Understand authentication, validation, and error handling simultaneously

**Workflow**:
```
Scout-1 → Auth code
Scout-2 → Validation code   (all run in parallel)
Scout-3 → Error handling
     ↓ (all outputs combined)
Worker → Synthesize findings and create improvement plan
```

**SDK Execution**:
```json
{
  "tasks": [
    {
      "agent": "scout",
      "task": "Find all authentication code. List implementation files, key functions, security checks used."
    },
    {
      "agent": "scout",
      "task": "Find all input validation code. List validation patterns, libraries used, coverage areas."
    },
    {
      "agent": "scout",
      "task": "Find all error handling code. List error types, where they're caught, logging patterns."
    }
  ]
}
```

**Then second parallel batch**:
```json
{
  "agent": "reviewer",
  "task": "Based on these findings from parallel scouts:\n\n{previous}\n\nCreate a security audit report identifying vulnerabilities and gaps in authentication, validation, and error handling."
}
```

**Parallel Execution Benefits**:
- All three scouts run concurrently (max 4 parallel by default)
- Each scout independently explores its domain
- Results stream in real-time
- Total time ≈ max(scout1, scout2, scout3) instead of scout1 + scout2 + scout3
- Worker receives combined context for synthesis

---

## Example 3: Refactoring Decision Flow

**Goal**: Plan database layer refactoring with different complexity levels

**Workflow**:
```
Scout → Analyze current DB layer
  ↓ {previous}
Planner → Simple refactoring plan
  ↓ {previous} (if accepted)
Worker → Implement simple version
```

**OR**:
```
Scout → Analyze current DB layer
  ↓ {previous}
Planner → Advanced refactoring plan
  ↓ {previous} (if accepted)
Scout → Find all usages of old API
  ↓ {previous}
Planner → Migration plan
  ↓ {previous}
Worker → Implement migration
```

**SDK Execution - Simple Path**:
```json
{
  "chain": [
    {
      "agent": "scout",
      "task": "Analyze the database layer. Find all database access patterns, ORMs used, connection management."
    },
    {
      "agent": "planner",
      "task": "Based on: {previous}\n\nPropose a simple refactoring to extract database logic into a service layer. Keep changes minimal."
    },
    {
      "agent": "worker",
      "task": "Implement the simple refactoring: {previous}"
    }
  ]
}
```

---

## Example 4: Multi-Agent Code Review

**Goal**: Comprehensive code review from different angles

**Workflow**:
```
Reviewer → Security review
Reviewer → Performance review      (run in parallel)
Reviewer → Architecture review
     ↓ (all results)
Worker → Address all findings
```

**SDK Execution**:
```json
{
  "tasks": [
    {
      "agent": "reviewer",
      "task": "Security review: Check for SQL injection, XSS, CSRF, auth bypass, sensitive data exposure, dependency vulnerabilities."
    },
    {
      "agent": "reviewer",
      "task": "Performance review: Check for N+1 queries, unoptimized loops, unnecessary allocations, caching opportunities."
    },
    {
      "agent": "reviewer",
      "task": "Architecture review: Check for SOLID principles, separation of concerns, testability, maintainability."
    }
  ]
}
```

Then:
```json
{
  "agent": "worker",
  "task": "Based on these three review perspectives: {previous}\n\nCreate a prioritized list of improvements and implement the highest-impact changes."
}
```

---

## Example 5: Learning & Documentation

**Goal**: Understand a complex module and create documentation

**Workflow**:
```
Scout → Understand module structure
  ↓ {previous}
Scout → Deep dive into key functions
  ↓ {previous}
Planner → Create documentation outline
  ↓ {previous}
Worker → Write comprehensive documentation
```

**SDK Execution**:
```json
{
  "chain": [
    {
      "agent": "scout",
      "task": "Understand the TypeScript compiler module. Find the main entry points, key exports, module structure."
    },
    {
      "agent": "scout",
      "task": "Based on the module structure from: {previous}\n\nDive deep into the transform pipeline. Find key transformation functions and their relationships."
    },
    {
      "agent": "planner",
      "task": "Based on these findings: {previous}\n\nCreate an outline for API documentation including main concepts, key classes, and usage patterns."
    },
    {
      "agent": "worker",
      "task": "Using this outline: {previous}\n\nWrite comprehensive API documentation with code examples."
    }
  ]
}
```

---

## Real-World Command Examples

**Interactive Commands in pi**:

```
# Single agent for quick lookup
Use scout to find all webhook implementations

# Explicit agent selection
Use planner to suggest how to add caching to the session layer

# Chain workflow via template
/implement add database connection pooling

# Another workflow template
/scout-and-plan refactor authentication to support SAML

# Review and iterate template
/implement-and-review add structured logging to all API endpoints

# Parallel scouts for parallel analysis
Run 3 scouts: one to find all API routes, one to find database queries, one to find error handlers
```

**SDK Usage**:

```typescript
// Single agent call
await session.prompt(`
Use subagent: agent=scout, task="Find all async/await usage"
`);

// Chain workflow
await session.prompt(`
Use subagent with chain:
1. scout: "Find React component structure"
2. planner: "Based on {previous}, plan state management refactor"
3. worker: "Implement according to {previous}"
`);

// Parallel scouts
await session.prompt(`
Use subagent with 3 parallel scouts:
1. Find GraphQL resolvers
2. Find REST endpoints
3. Find WebSocket handlers
`);
```

---

## Customizing Agents

Create project-specific agents in `.pi/agents/`:

```markdown
---
name: database-expert
description: Specialized in database design and optimization
tools: read, grep, find, ls, bash
model: claude-opus-4-5
---

You are a database expert specialized in:
- Schema design and normalization
- Query optimization
- Index strategies
- Migration planning
- Performance analysis

When analyzing databases:
1. Look at schema definitions first
2. Check query patterns and frequency
3. Identify missing indexes
4. Suggest normalization improvements
5. Propose optimization opportunities
```

Then use in workflow:

```json
{
  "agentScope": "both",
  "chain": [
    {
      "agent": "scout",
      "task": "Analyze the database schema and find all queries"
    },
    {
      "agent": "database-expert",
      "task": "Based on: {previous}\n\nOptimize the schema and queries for performance"
    },
    {
      "agent": "worker",
      "task": "Implement the optimizations: {previous}"
    }
  ]
}
```

---

## Key Interaction Patterns

### Pattern 1: Fact-gathering → Planning → Execution
```
scout → planner → worker
```
Scout provides raw findings, planner creates strategy, worker executes.

### Pattern 2: Parallel Analysis → Synthesis
```
[scout-A, scout-B, scout-C] → worker
```
Multiple scouts analyze different domains, worker synthesizes insights.

### Pattern 3: Implementation → Review → Refinement
```
worker → reviewer → worker
```
Worker codes, reviewer critiques, worker refines.

### Pattern 4: Multi-perspective Analysis
```
[reviewer-A, reviewer-B, reviewer-C] → worker
```
Different reviewers check different angles, worker prioritizes fixes.

### Pattern 5: Layered Exploration
```
scout-1 → scout-2 → planner → worker
```
First scout gets overview, second scout drills down, planner designs, worker implements.
