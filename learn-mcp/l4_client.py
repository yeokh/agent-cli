"""Stage 4 client: LLM chat loop with Anthropic Haiku and MCP tool discovery."""

import asyncio
import os
import sys
from contextlib import AsyncExitStack

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPToolset

from config import SERVER1_PORT, SERVER2_PORT, server_url


async def build_system_prompt(toolsets: list[MCPToolset]) -> str:
    lines = [
        "You are a helpful assistant with access to MCP tools.",
        "",
        "Available tools:",
    ]
    for toolset in toolsets:
        for tool in await toolset.list_tools():
            description = tool.description or "No description provided."
            lines.append(f"- {tool.name}: {description}")
    lines.extend(
        [
            "",
            "Decide whether to answer directly or call a tool. "
            "Use a tool when it helps answer the user's request.",
        ]
    )
    return "\n".join(lines)


async def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Set ANTHROPIC_API_KEY to run the Stage 4 chat client.", file=sys.stderr)
        sys.exit(1)

    toolsets = [
        MCPToolset(server_url(SERVER1_PORT), id="l4-server1"),
        MCPToolset(server_url(SERVER2_PORT), id="l4-server2"),
    ]

    async with AsyncExitStack() as stack:
        for toolset in toolsets:
            await stack.enter_async_context(toolset)

        system_prompt = await build_system_prompt(toolsets)
        agent = Agent(
            "anthropic:claude-haiku-4-5",
            system_prompt=system_prompt,
            toolsets=toolsets,
        )

        print("Stage 4 chat client (type 'quit' to exit)")
        async with agent:
            while True:
                user_input = input("You: ").strip()
                if user_input.lower() in {"quit", "exit"}:
                    break
                if not user_input:
                    continue
                result = await agent.run(user_input)
                print(f"Assistant: {result.output}")


if __name__ == "__main__":
    asyncio.run(main())
