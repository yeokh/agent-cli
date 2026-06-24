"""Stage 5 server 1: authenticated echo and reverse tools."""

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from config import API_KEY, HOST, SERVER1_PORT

mcp = FastMCP(
    "L5Server1",
    auth=StaticTokenVerifier(
        tokens={API_KEY: {"client_id": "learn-mcp-client", "scopes": []}}
    ),
)


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
