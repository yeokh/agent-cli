"""Stage 5 server 2: authenticated uppercase and lowercase tools."""

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from config import API_KEY, HOST, SERVER2_PORT

mcp = FastMCP(
    "L5Server2",
    auth=StaticTokenVerifier(
        tokens={API_KEY: {"client_id": "learn-mcp-client", "scopes": []}}
    ),
)


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
