#!/usr/bin/env python3
"""
Level 5 — Google ADK multi-agent orchestration.

root_agent orchestrates two sub-agents:
  web_agent   — fetches URLs
  file_agent  — reads project files, writes to ./output/

ADK manages routing, session state, and sub-agent lifecycles.
"""
import asyncio
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from rich.console import Console
from config import LEVEL_STYLE, OUTPUT_DIR, BASE_DIR, get_api_config, get_native_model, handle_slash, load_state, validate_api_key

LEVEL        = 5
LABEL, STYLE = LEVEL_STYLE[LEVEL]
console      = Console()

ROOT_INSTRUCTION = (
    "You are an orchestrating assistant with two sub-agents: "
    "web_agent (fetch URLs) and file_agent (list files, write output). "
    "Delegate to the right sub-agent and summarise the result."
)
WEB_INSTRUCTION  = "Fetch URLs and summarise the content."
FILE_INSTRUCTION = "List project files and write results to ./output/."


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def web_fetch(url: str) -> str:
    """Fetch content from a URL. Args: url — http/https URL. Returns: response text."""
    import httpx, json
    console.print(f"\n[yellow]  → web_fetch({url})[/]")
    try:
        r = httpx.get(url, follow_redirects=True, timeout=30,
                      headers={"User-Agent": "learn-agent-adk/1.0"})
        text = r.text[:8_000]
        console.print(f"[dim yellow]  ← {r.status_code}  {len(text)} chars[/]")
        return json.dumps({"status": r.status_code, "text": text})
    except Exception as e:
        console.print(f"[red]  ← Error: {e}[/]")
        return f"Error: {e}"


def list_project_files(path: str = ".") -> str:
    """List files in the project folder. Args: path — relative path."""
    console.print(f"\n[yellow]  → list_project_files({path})[/]")
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


def save_output_file(filename: str, content: str) -> str:
    """Write content to ./output/. Args: filename — file name; content — text."""
    console.print(f"\n[yellow]  → save_output_file({filename})[/]")
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


# ---------------------------------------------------------------------------
# ADK model builder
# ---------------------------------------------------------------------------

def build_litellm(provider, model_id):
    from google.adk.models.lite_llm import LiteLlm
    native = get_native_model(model_id, provider)
    config = get_api_config(provider)
    if provider == "openrouter":
        lid = native if native.startswith("openrouter/") else f"openrouter/{native}"
        return LiteLlm(model=lid, api_base="https://openrouter.ai/api/v1",
                       api_key=config["api_key"], max_tokens=4096)
    if provider == "openai":
        lid = native if native.startswith("openai/") else f"openai/{native}"
        return LiteLlm(model=lid, api_base="https://api.openai.com/v1",
                       api_key=config["api_key"], max_tokens=4096)
    # anthropic — LiteLlm reads ANTHROPIC_API_KEY from env
    os.environ["ANTHROPIC_API_KEY"] = config["api_key"]
    return LiteLlm(model=native, max_tokens=4096)


# ---------------------------------------------------------------------------
# ADK event display
# ---------------------------------------------------------------------------

def print_event(event):
    content = getattr(event, "content", None)
    if not content:
        return
    author = getattr(event, "author", "")
    for part in getattr(content, "parts", []) or []:
        text = getattr(part, "text", None)
        if text and text.strip() and author != "user":
            console.print(f"\n[{STYLE}]{LABEL}:[/] ", end="")
            console.print(text.strip(), style=STYLE, markup=False, highlight=False)
        fc = getattr(part, "function_call", None)
        if fc:
            args = {k: str(v)[:60] for k, v in dict(getattr(fc, "args", {}) or {}).items()}
            console.print(f"\n[yellow]  [agent] → {fc.name}({args})[/]")
        fr = getattr(part, "function_response", None)
        if fr:
            resp = getattr(fr, "response", {})
            snippet = str(resp.get("result", resp) if isinstance(resp, dict) else resp)[:200]
            console.print(f"[dim yellow]  [agent] ← {fr.name}: {snippet}[/]")


# ---------------------------------------------------------------------------
# Interactive session
# ---------------------------------------------------------------------------

async def run_session(provider, model_id):
    from google.adk.agents import LlmAgent
    from google.adk.runners import InMemoryRunner
    from google.adk.tools.agent_tool import AgentTool
    from google.genai import types as genai_types

    model = build_litellm(provider, model_id)

    web_agent  = LlmAgent(name="web_agent",  model=model, instruction=WEB_INSTRUCTION,  tools=[web_fetch])
    file_agent = LlmAgent(name="file_agent", model=model, instruction=FILE_INSTRUCTION, tools=[list_project_files, save_output_file])
    root_agent = LlmAgent(name="root_agent", model=model, instruction=ROOT_INSTRUCTION,
                          tools=[AgentTool(agent=web_agent), AgentTool(agent=file_agent)])

    runner  = InMemoryRunner(agent=root_agent, app_name="learn_agent_l5")
    session = await runner.session_service.create_session(app_name="learn_agent_l5", user_id="user")

    print("ADK session ready.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            action = handle_slash(user_input, load_state(), console, LEVEL)
            if action == "exit":
                break
            if action == "clear":
                session = await runner.session_service.create_session(
                    app_name="learn_agent_l5", user_id="user")
                print("Session reset.")
                continue
            if action == "rebuild":
                return "rebuild"
            continue

        msg = genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=user_input)])
        try:
            async for event in runner.run_async(user_id="user", session_id=session.id, new_message=msg):
                print_event(event)
        except Exception as e:
            print(f"\nAgent error: {e}")
        print()


def run(state):
    provider = state.get("provider")
    model_id = state.get("model")

    if not provider or not model_id:
        print("No provider configured. Run main.py first.")
        return
    if not validate_api_key(provider, console):
        return

    print(f"\nLevel 5 — Google ADK multi-agent  [{provider} / {model_id}]")
    print("Sub-agents: web_agent  file_agent")
    print("Commands: /switch /provider /model /clear /exit /help\n")

    try:
        result = asyncio.run(run_session(provider, model_id))
    except Exception as e:
        print(f"Fatal error: {e}")
        return

    if result == "rebuild":
        run(load_state())


if __name__ == "__main__":
    while True:
        state = load_state()
        run(state)
        break
