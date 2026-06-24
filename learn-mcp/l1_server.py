"""Stage 1 server: one tool (echo)."""

from fastmcp import FastMCP

from config import HOST, SERVER1_PORT

mcp = FastMCP("L1Server")


@mcp.tool
def echo(text: str) -> str:
    """Return the input text unchanged."""
    return text


if __name__ == "__main__":
    mcp.run(transport="http", host=HOST, port=SERVER1_PORT)
