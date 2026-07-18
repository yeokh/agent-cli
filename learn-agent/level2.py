#!/usr/bin/env python3
"""
Level 2 — Direct HTTP POST with chat history as context.

Every request includes all prior messages.
The LLM can refer back to earlier turns.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from config import LEVEL_STYLE, handle_slash, load_state, stream_chat, validate_api_key

LEVEL        = 2
LABEL, STYLE = LEVEL_STYLE[LEVEL]
console      = Console()

SYSTEM = "You are a helpful, concise assistant."


def run(state):
    provider = state.get("provider")
    model    = state.get("model")

    if not provider or not model:
        print("No provider configured. Run main.py first.")
        return
    if not validate_api_key(provider, console):
        return

    print(f"\nLevel 2 — Direct HTTP, with context  [{provider} / {model}]")
    print("Full history sent with every request — LLM remembers the conversation.")
    print("Commands: /switch /provider /model /clear /exit /help\n")

    # System message + growing conversation history
    history = [{"role": "system", "content": SYSTEM}]

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
                history = [{"role": "system", "content": SYSTEM}]
                print("Cleared.")
                continue
            if action == "rebuild":
                state    = load_state()
                provider = state["provider"]
                model    = state["model"]
                history  = [{"role": "system", "content": SYSTEM}]
                if not validate_api_key(provider, console):
                    return
                print(f"Using {provider} / {model}")
            continue

        history.append({"role": "user", "content": user_input})

        console.print(f"\n[{STYLE}]{LABEL}:[/] ", end="")
        response = stream_chat(history, provider, model, console, STYLE)

        if response:
            history.append({"role": "assistant", "content": response})
        print()


if __name__ == "__main__":
    while True:
        state = load_state()
        run(state)
        break
