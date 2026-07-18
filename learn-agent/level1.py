#!/usr/bin/env python3
"""
Level 1 — Direct HTTP POST, no context.

Each message is sent to the LLM alone.
The LLM has no memory of prior turns.
A local history is kept for display only — never sent to the API.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from config import LEVEL_STYLE, handle_slash, load_state, stream_chat, validate_api_key

LEVEL        = 1
LABEL, STYLE = LEVEL_STYLE[LEVEL]
console      = Console()


def run(state):
    provider = state.get("provider")
    model    = state.get("model")

    if not provider or not model:
        print("No provider configured. Run main.py first.")
        return
    if not validate_api_key(provider, console):
        return

    print(f"\nLevel 1 — Direct HTTP, no context  [{provider} / {model}]")
    print("Each message sent alone — LLM has no memory of prior turns.")
    print("Commands: /switch /provider /model /clear /exit /help\n")

    history = []  # display log only — never sent to the LLM

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
                history.clear()
                print("Cleared.")
                continue
            if action == "rebuild":
                state    = load_state()
                provider = state["provider"]
                model    = state["model"]
                history.clear()
                if not validate_api_key(provider, console):
                    return
                print(f"Using {provider} / {model}")
            continue

        # Send only the current message — no history
        messages = [{"role": "user", "content": user_input}]

        console.print(f"\n[{STYLE}]{LABEL}:[/] ", end="")
        response = stream_chat(messages, provider, model, console, STYLE)

        history.append({"role": "user",      "content": user_input})
        history.append({"role": "assistant", "content": response})
        print()


if __name__ == "__main__":
    while True:
        state = load_state()
        run(state)
        break
