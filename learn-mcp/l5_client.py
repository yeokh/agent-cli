"""Stage 5 client: connect to authenticated servers with a shared API key."""

import asyncio
from contextlib import AsyncExitStack

from pydantic_ai.mcp import MCPToolset

from config import API_KEY, SERVER1_PORT, SERVER2_PORT, SAMPLE_ARGS, server_url


async def main() -> None:
    servers = [
        ("server1", server_url(SERVER1_PORT)),
        ("server2", server_url(SERVER2_PORT)),
    ]
    toolsets = [
        MCPToolset(url, id=name, auth=API_KEY) for name, url in servers
    ]

    async with AsyncExitStack() as stack:
        for toolset in toolsets:
            await stack.enter_async_context(toolset)

        for (name, _), toolset in zip(servers, toolsets, strict=True):
            tools = await toolset.list_tools()
            print(f"{name}: discovered {len(tools)} tool(s) (authenticated)")

        print()
        for toolset in toolsets:
            for tool in await toolset.list_tools():
                args = SAMPLE_ARGS.get(tool.name, {"text": "hello"})
                result = await toolset.direct_call_tool(tool.name, args)
                print(f"{tool.name}({args}) -> {result!r}")


if __name__ == "__main__":
    asyncio.run(main())
