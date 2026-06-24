"""Stage 3 server 1: echo and reverse."""

from fastmcp import FastMCP

from config import HOST, SERVER1_PORT

mcp = FastMCP("L3Server1")


@mcp.tool
def echo(text: str) -> str:
    """Return the input text unchanged."""
    return text


@mcp.tool
def reverse(text: str) -> str:
    """Reverse the input text."""
    return text[::-1]


if __name__ == "__main__":
    mcp.run(transport="http", host=HOST, port=SERVER1_PORT)
