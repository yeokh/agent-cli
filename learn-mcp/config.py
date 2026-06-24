"""Shared settings for the MCP tutorial stages."""

import os

API_KEY = os.environ.get("MCP_API_KEY", "learn-mcp-secret-key")

HOST = "127.0.0.1"

SERVER1_PORT = 8081
SERVER2_PORT = 8082

SAMPLE_ARGS: dict[str, dict[str, str]] = {
    "echo": {"text": "hello"},
    "reverse": {"text": "hello"},
    "uppercase": {"text": "hello"},
    "lowercase": {"text": "HELLO"},
}


def server_url(port: int) -> str:
    return f"http://{HOST}:{port}/mcp"


def base_url(port: int) -> str:
    return f"http://{HOST}:{port}"
