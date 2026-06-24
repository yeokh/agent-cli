"""Stage 2 client: discover tools via /tools, then call each one."""

import asyncio

import httpx
from pydantic_ai.mcp import MCPToolset

from config import SERVER1_PORT, SAMPLE_ARGS, base_url, server_url


async def main() -> None:
    tools_url = f"{base_url(SERVER1_PORT)}/tools"
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            response = await http.get(tools_url)
            response.raise_for_status()
            tools = response.json()["tools"]
    except httpx.ReadTimeout as exc:
        raise SystemExit(
            f"Timed out waiting for {tools_url}. "
            "Is l2_server.py running? If a previous server is stuck, "
            f"stop it with: fuser -k {SERVER1_PORT}/tcp"
        ) from exc
    except httpx.ConnectError as exc:
        raise SystemExit(
            f"Could not connect to {tools_url}. Start the server first: python l2_server.py"
        ) from exc

    print(f"Discovered {len(tools)} tool(s) from /tools:")
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description']}")

    toolset = MCPToolset(server_url(SERVER1_PORT))
    async with toolset:
        for tool in tools:
            name = tool["name"]
            args = SAMPLE_ARGS.get(name, {"text": "hello"})
            result = await toolset.direct_call_tool(name, args)
            print(f"{name}({args}) -> {result!r}")


if __name__ == "__main__":
    asyncio.run(main())
