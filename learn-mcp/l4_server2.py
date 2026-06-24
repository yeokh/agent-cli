"""Stage 4 server 2: uppercase and lowercase (for the LLM chat client)."""

from fastmcp import FastMCP

from config import HOST, SERVER2_PORT

mcp = FastMCP("L4Server2")


@mcp.tool
def uppercase(text: str) -> str:
    """Convert text to uppercase."""
    return text.upper()


@mcp.tool
def lowercase(text: str) -> str:
    """Convert text to lowercase."""
    return text.lower()


if __name__ == "__main__":
    mcp.run(transport="http", host=HOST, port=SERVER2_PORT)
