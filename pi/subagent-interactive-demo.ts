/**
 * Sub-Agent Interactive Demonstration
 * 
 * This script demonstrates all three sub-agent modes:
 * 1. Single agent (basic task delegation)
 * 2. Parallel execution (concurrent multi-scout runs)
 * 3. Chain execution (sequential with context passing)
 * 
 * Run with: npx ts-node subagent-interactive-demo.ts
 */

import { createAgentSession, ModelRuntime, SessionManager } from "@earendil-works/pi-coding-agent";

type Mode = "single" | "parallel" | "chain";

interface SubagentCall {
  mode: Mode;
  description: string;
  params: Record<string, unknown>;
}

const DEMONSTRATIONS: SubagentCall[] = [
  {
    mode: "single",
    description: "Scout finds authentication code",
    params: {
      agent: "scout",
      task: "Find all files that implement authentication. List file paths and key functions.",
    },
  },

  {
    mode: "single",
    description: "Planner creates a refactoring plan",
    params: {
      agent: "planner",
      task:
        "Create a plan to extract database logic from main.ts into a separate db-service module. List the steps needed.",
    },
  },

  {
    mode: "parallel",
    description: "Two scouts in parallel: one finds models, one finds providers",
    params: {
      tasks: [
        {
          agent: "scout",
          task: 'Find all TypeScript interfaces named "*Model" or "*Config". Show file paths and line numbers.',
        },
        {
          agent: "scout",
          task: "Find all provider implementations. List all files and their key exports.",
        },
      ],
    },
  },

  {
    mode: "chain",
    description: "Chain: scout → planner → (decision point, then worker if needed)",
    params: {
      chain: [
        {
          agent: "scout",
          task:
            "Find all error handling code. List patterns used, error types defined, and where they're thrown from.",
        },
        {
          agent: "planner",
          task:
            "Based on these error handling patterns: {previous}\n\nCreate a plan to standardize error handling across the codebase.",
        },
      ],
    },
  },
];

async function runDemo(): Promise<void> {
  console.log("╔════════════════════════════════════════════════════════════════╗");
  console.log("║         Pi Sub-Agent Interactive Demonstration                 ║");
  console.log("╚════════════════════════════════════════════════════════════════╝\n");

  // Initialize session
  console.log("📍 Initializing agent session...\n");
  const modelRuntime = await ModelRuntime.create();

  const { session } = await createAgentSession({
    sessionManager: SessionManager.inMemory(),
    modelRuntime,
  });

  let messageCount = 0;
  let toolCallCount = 0;
  let currentToolName = "";

  session.subscribe((event) => {
    // Stream text output
    if (event.type === "message_update") {
      if (event.assistantMessageEvent.type === "text_delta") {
        process.stdout.write(event.assistantMessageEvent.delta);
      }
    }

    // Track tool invocations
    if (event.type === "tool_execution_start") {
      if (event.toolName === "subagent") {
        toolCallCount++;
        currentToolName = event.toolName;
        // Tool parameters logged by subagent tool itself
      }
    }

    // Track message completion
    if (event.type === "message_end") {
      messageCount++;
    }
  });

  // Demonstrate each mode
  for (const demo of DEMONSTRATIONS) {
    console.log(`\n${"═".repeat(70)}`);
    console.log(
      `\n🔷 DEMONSTRATION #${DEMONSTRATIONS.indexOf(demo) + 1}: ${demo.mode.toUpperCase()}`,
    );
    console.log(`   ${demo.description}\n`);
    console.log("Parameters:");
    console.log(JSON.stringify(demo.params, null, 2));
    console.log(`\n${"─".repeat(70)}\n`);

    // Build the prompt
    let prompt: string;
    if (demo.mode === "single") {
      const params = demo.params as { agent: string; task: string };
      prompt = `
Delegate this task to the subagent tool using single mode:
- Agent: ${params.agent}
- Task: ${params.task}

Use the subagent tool with these exact parameters:
${JSON.stringify(demo.params, null, 2)}
      `.trim();
    } else if (demo.mode === "parallel") {
      const params = demo.params as { tasks: Array<{ agent: string; task: string }> };
      prompt = `
Delegate these ${params.tasks.length} tasks to run in parallel using the subagent tool:
${params.tasks.map((t, i) => `Task ${i + 1}: ${t.agent} - ${t.task}`).join("\n")}

Use the subagent tool with parallel mode:
${JSON.stringify(demo.params, null, 2)}
      `.trim();
    } else {
      // chain
      const params = demo.params as {
        chain: Array<{ agent: string; task: string }>;
      };
      prompt = `
Execute this workflow chain using the subagent tool:
${params.chain
  .map(
    (step, i) =>
      `Step ${i + 1}: ${step.agent} - "${step.task}"${step.task.includes("{previous}") ? " [uses output from previous step]" : ""}`,
  )
  .join("\n")}

Use the subagent tool with chain mode:
${JSON.stringify(demo.params, null, 2)}
      `.trim();
    }

    toolCallCount = 0;
    messageCount = 0;

    try {
      await session.prompt(prompt);
      console.log(`\n\n✓ Complete. Message count: ${messageCount}, Tool invocations: ${toolCallCount}`);
    } catch (error) {
      console.error(`\n✗ Error in demonstration:`, error);
    }

    // Pause between demos
    if (DEMONSTRATIONS.indexOf(demo) < DEMONSTRATIONS.length - 1) {
      console.log("\n(Next demonstration in 2 seconds...)\n");
      await new Promise((resolve) => setTimeout(resolve, 2000));
    }
  }

  console.log(`\n${"═".repeat(70)}\n`);
  console.log("╔════════════════════════════════════════════════════════════════╗");
  console.log("║                   Demonstration Complete                       ║");
  console.log("╠════════════════════════════════════════════════════════════════╣");
  console.log("║                                                                ║");
  console.log("║  Key Concepts Demonstrated:                                    ║");
  console.log("║  • Single agent: One task to one agent                         ║");
  console.log("║  • Parallel: Multiple agents run concurrently (max 8)          ║");
  console.log("║  • Chain: Sequential execution with {previous} placeholder      ║");
  console.log("║                                                                ║");
  console.log("║  Each subagent:                                                ║");
  console.log("║  • Runs in isolated subprocess                                 ║");
  console.log("║  • Has own context window, model, tools                        ║");
  console.log("║  • Streams output in real-time                                 ║");
  console.log("║  • Returns usage stats (tokens, cost, cache)                   ║");
  console.log("║                                                                ║");
  console.log("╚════════════════════════════════════════════════════════════════╝\n");

  session.dispose();
}

runDemo().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
