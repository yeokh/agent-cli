#
# export CURSOR_API_KEY="crsr_xxx"
# uv run cursor_client.py
#
import os
import secrets

import cursor_sdk._store_callback as _store_callback
import cursor_sdk._tool_callback as _tool_callback


def _safe_auth_token() -> str:
    # cursor-sdk 0.1.7 passes callback tokens as CLI args; values starting
    # with "-" are misparsed as flags ("Missing value for --tool-callback-auth-token").
    while True:
        token = secrets.token_urlsafe(32)
        if not token.startswith("-"):
            return token


_store_callback._new_auth_token = _safe_auth_token
_tool_callback._new_auth_token = _safe_auth_token

#
# Above is a workaround fix for cursor-sdk.  Can remove once fixed.
#
from cursor_sdk import Agent, AgentOptions, LocalAgentOptions

def run_cursor_agent():
    # Retrieve the API key from environment variables
    api_key = os.environ.get("CURSOR_API_KEY")
    
    if not api_key:
        raise ValueError("CURSOR_API_KEY environment variable not set.")

    # Define options for the agent, targeting the local workspace directory
    agent_options = AgentOptions(
        api_key=api_key,
        model="composer-2.5",
        local=LocalAgentOptions(cwd=".")
    )

    print("Initializing Cursor AI Agent...")
    
    # Create and run the agent context
    with Agent.create(agent_options) as agent:
        prompt = "Create a basic Python function in a new file utils.py that calculates Fibonacci numbers."
        print(f"Sending prompt to agent: '{prompt}'")
        
        run = agent.send(prompt)
        response = run.text()

        print("\n--- Agent Execution Complete ---")
        print(response)

if __name__ == "__main__":
    run_cursor_agent()
