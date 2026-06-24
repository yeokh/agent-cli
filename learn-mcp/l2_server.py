"""Stage 2 server: echo and reverse tools, plus a /tools discovery endpoint."""

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from config import HOST, SERVER1_PORT

mcp = FastMCP("L2Server")


@mcp.tool
def echo(text: str) -> str:
    """Return the input text unchanged."""
    return text


@mcp.tool
def reverse(text: str) -> str:
    """Reverse the input text."""
    return text[::-1]


@mcp.custom_route("/tools", methods=["GET"])
async def list_tools_endpoint(_request: Request) -> JSONResponse:
    # Use the local provider directly. Calling mcp.list_tools() from a custom
    # HTTP route can hang because that path runs MCP middleware meant for /mcp.
    tools = await mcp.local_provider.list_tools()
    return JSONResponse(
        {
            "tools": [
                {"name": tool.name, "description": tool.description or ""}
                for tool in tools
            ]
        }
    )


if __name__ == "__main__":
    mcp.run(transport="http", host=HOST, port=SERVER1_PORT)
