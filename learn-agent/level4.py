#!/usr/bin/env python3
"""
Level 4 — Pydantic AI ReAct loop with tools.

The agent reasons and acts in a loop using three tools:
  fetch_web(url)              — fetch a URL
  read_folder(path)           — list project files
  write_output(filename, text)— save a file to ./output/

Tool calls print in yellow. Final answer streams in magenta.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from config import LEVEL_STYLE, OUTPUT_DIR, BASE_DIR, build_pydantic_model, handle_slash, load_state, validate_api_key

LEVEL        = 4
LABEL, STYLE = LEVEL_STYLE[LEVEL]
console      = Console()

SYSTEM = (
    "You are a helpful assistant with tools. "
    "Use fetch_web to get information from URLs, "
    "read_folder to list project files, "
    "and write_output to save results to disk."
)


def make_tools(agent):
    @agent.tool_plain
    def fetch_web(url: str) -> str:
        """Fetch text content from a URL. Args: url — http/https URL."""
        import httpx
        console.print(f"\n[yellow]  → fetch_web({url})[/]")
        try:
            r = httpx.get(url, follow_redirects=True, timeout=30,
                          headers={"User-Agent": "learn-agent/1.0"})
            text = r.text[:8_000]
            console.print(f"[dim yellow]  ← {r.status_code}  {len(text)} chars[/]")
            return text
        except Exception as e:
            console.print(f"[red]  ← Error: {e}[/]")
            return f"Error: {e}"

    @agent.tool_plain
    def read_folder(path: str = ".") -> str:
        """List files in the project folder. Args: path — relative path (default: project root)."""
        console.print(f"\n[yellow]  → read_folder({path})[/]")
        try:
            target = (BASE_DIR / path).resolve()
            if not str(target).startswith(str(BASE_DIR.resolve())):
                return "Error: path outside project"
            items = [
                ("📁 " if p.is_dir() else "📄 ") + p.name
                for p in sorted(target.iterdir())
                if not p.name.startswith(".")
            ]
            console.print(f"[dim yellow]  ← {len(items)} items[/]")
            return "\n".join(items) or "(empty)"
        except Exception as e:
            return f"Error: {e}"

    @agent.tool_plain
    def write_output(filename: str, content: str) -> str:
        """Write content to ./output/. Args: filename — file name; content — text to write."""
        console.print(f"\n[yellow]  → write_output({filename})[/]")
        try:
            OUTPUT_DIR.mkdir(exist_ok=True)
            target = (OUTPUT_DIR / filename).resolve()
            if not str(target).startswith(str(OUTPUT_DIR.resolve())):
                return "Error: path outside output/"
            target.write_text(content, encoding="utf-8")
            console.print(f"[dim yellow]  ← wrote {target.stat().st_size} bytes[/]")
            return f"Saved to output/{filename}"
        except Exception as e:
            return f"Error: {e}"


async def agent_turn(agent, user_input, history):
    """Run one ReAct turn. Returns updated history."""
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

    print(f"\nLevel 4 — Pydantic AI ReAct + tools  [{provider} / {model_id}]")
    print("Tools: fetch_web  read_folder  write_output")
    print("Commands: /switch /provider /model /clear /exit /help\n")

    def build():
        from pydantic_ai import Agent
        ag = Agent(build_pydantic_model(provider, model_id), system_prompt=SYSTEM)
        make_tools(ag)
        return ag

    try:
        agent = build()
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
                    agent = build()
                    print(f"Using {provider} / {model_id}")
                except Exception as e:
                    print(f"Failed to rebuild: {e}")
                    return
            continue

        try:
            history = asyncio.run(agent_turn(agent, user_input, history))
            print()
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    while True:
        state = load_state()
        run(state)
        break
