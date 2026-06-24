"""Stage 1 client: call echo directly via Pydantic AI MCPToolset."""

import asyncio

from pydantic_ai.mcp import MCPToolset

from config import SERVER1_PORT, server_url


async def main() -> None:
    toolset = MCPToolset(server_url(SERVER1_PORT))
    async with toolset:
        result = await toolset.direct_call_tool("echo", {"text": "hello"})
        print(f"echo('hello') -> {result!r}")


if __name__ == "__main__":
    asyncio.run(main())
