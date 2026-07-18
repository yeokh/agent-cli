#!/usr/bin/env python3
"""learn-agent — progressive LLM interaction demo."""
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

from config import (
    LEVEL_DESCRIPTIONS, LEVEL_STYLE,
    get_available_providers, get_available_models,
    load_state, save_state,
)

SCRIPTS = {
    1: "level1.py",
    2: "level2.py",
    3: "level3.py",
    4: "level4.py",
    5: "level5/agent.py",
}


def main():
    state = load_state()

    # Auto-configure provider from available API keys
    if not state.get("provider"):
        available = get_available_providers()
        if not available:
            print("No API key found. Set OPENROUTER_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY.")
            sys.exit(1)
        state["provider"] = available[0]
        models = get_available_models(state["provider"])
        state["model"] = models[0] if models else None
        save_state(state)

    current = state.get("current_level", 1)

    while True:
        state    = load_state()
        provider = state.get("provider", "?")
        model    = state.get("model", "?")

        print(f"\nlearn-agent  [{provider} / {model}]")
        print()
        for n, desc in LEVEL_DESCRIPTIONS.items():
            mark  = ">" if n == current else " "
            label = LEVEL_STYLE[n][0]
            print(f"  {mark} {n}  {label:<18}  {desc}")
        print()

        try:
            raw = input(f"Select AI level [1-5, Enter={current}]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye!")
            break

        if raw:
            try:
                n = int(raw)
                if 1 <= n <= 5:
                    current = n
                else:
                    print("Enter a number 1-5.")
                    continue
            except ValueError:
                print("Enter a number 1-5.")
                continue

        state["current_level"] = current
        save_state(state)

        result = subprocess.run(
            [sys.executable, str(PROJECT_DIR / SCRIPTS[current])],
            cwd=str(PROJECT_DIR),
        )

        # exit codes 11-15 mean /switch was used inside a level
        if 11 <= result.returncode <= 15:
            current = result.returncode - 10


if __name__ == "__main__":
    main()
