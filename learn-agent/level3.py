#!/usr/bin/env python3
"""
Level 3 — Pydantic AI with system prompt and session management.

The pydantic-ai Agent handles role separation, message serialisation,
and session state. No tools registered.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from config import LEVEL_STYLE, build_pydantic_model, handle_slash, load_state, validate_api_key

LEVEL        = 3
LABEL, STYLE = LEVEL_STYLE[LEVEL]
console      = Console()

SYSTEM = "You are a helpful assistant. You have full memory of this conversation."


async def chat_turn(agent, user_input, history):
    """Stream one response. Returns the updated message history."""
    async with agent.run_stream(user_input, message_history=history) as stream:
        console.print(f"\n[{STYLE}]{LABEL}:[/] ", end="")
        async for delta in stream.stream_text(delta=True):
            console.print(delta, end="", style=STYLE, markup=False, highlight=False)
        console.print()
        return stream.all_messages()


def run(state):
    provider = state.get("provider")
    model_id = state.get("model")

    if not provider or not model_id:
        print("No provider configured. Run main.py first.")
        return
    if not validate_api_key(provider, console):
        return

    print(f"\nLevel 3 — Pydantic AI, system prompt + session  [{provider} / {model_id}]")
    print("pydantic-ai manages roles, message serialisation, and session state.")
    print("Commands: /switch /provider /model /clear /exit /help\n")

    try:
        from pydantic_ai import Agent
        agent = Agent(build_pydantic_model(provider, model_id), system_prompt=SYSTEM)
    except Exception as e:
        print(f"Failed to build agent: {e}")
        return

    history = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            action = handle_slash(user_input, state, console, LEVEL)
            if action == "exit":
                break
            if action == "clear":
                history = []
                print("Cleared.")
                continue
            if action == "rebuild":
                state    = load_state()
                provider = state["provider"]
                model_id = state["model"]
                history  = []
                if not validate_api_key(provider, console):
                    return
                try:
                    agent = Agent(build_pydantic_model(provider, model_id), system_prompt=SYSTEM)
                    print(f"Using {provider} / {model_id}")
                except Exception as e:
                    print(f"Failed to rebuild agent: {e}")
                    return
            continue

        try:
            history = asyncio.run(chat_turn(agent, user_input, history))
            print()
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    while True:
        state = load_state()
        run(state)
        break
