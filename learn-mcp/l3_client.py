"""Stage 3 client: connect to two servers, discover tools, and call each."""

import asyncio
from contextlib import AsyncExitStack

from pydantic_ai.mcp import MCPToolset

from config import SERVER1_PORT, SERVER2_PORT, SAMPLE_ARGS, server_url


async def main() -> None:
    servers = [
        ("server1", server_url(SERVER1_PORT)),
        ("server2", server_url(SERVER2_PORT)),
    ]
    toolsets = [MCPToolset(url, id=name) for name, url in servers]

    async with AsyncExitStack() as stack:
        for toolset in toolsets:
            await stack.enter_async_context(toolset)

        for (name, _), toolset in zip(servers, toolsets, strict=True):
            tools = await toolset.list_tools()
            print(f"{name}: discovered {len(tools)} tool(s)")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description or ''}")

        print()
        for toolset in toolsets:
            for tool in await toolset.list_tools():
                args = SAMPLE_ARGS.get(tool.name, {"text": "hello"})
                result = await toolset.direct_call_tool(tool.name, args)
                print(f"{tool.name}({args}) -> {result!r}")


if __name__ == "__main__":
    asyncio.run(main())
