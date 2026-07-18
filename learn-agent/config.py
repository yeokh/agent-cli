"""Shared configuration, state management, and HTTP helpers for learn-agent."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Iterator, Optional

BASE_DIR = Path(__file__).parent
STATE_FILE = BASE_DIR / ".state.json"
OUTPUT_DIR = BASE_DIR / "output"

# ---------------------------------------------------------------------------
# Model catalog
# ---------------------------------------------------------------------------

MODELS: dict[str, dict] = {
    "deepseek/deepseek-r1": {
        "display": "DeepSeek R1  (reasoning model — shows thinking steps)",
        "openrouter": "deepseek/deepseek-r1",
        "openai": None,
        "anthropic": None,
    },
    "anthropic/claude-haiku-4.5": {
        "display": "Claude Haiku 4.5  (fast & efficient)",
        "openrouter": "anthropic/claude-haiku-4-5",
        "openai": None,
        "anthropic": "claude-haiku-4-5",
    },
    "openai/gpt-4o-mini": {
        "display": "GPT-4o Mini  (lightweight GPT)",
        "openrouter": "openai/gpt-4o-mini",
        "openai": "gpt-4o-mini",
        "anthropic": None,
    },
    "openai/gpt-4o": {
        "display": "GPT-4o  (full GPT flagship)",
        "openrouter": "openai/gpt-4o",
        "openai": "gpt-4o",
        "anthropic": None,
    },
    "ibm-granite/granite-4.1-8b": {
        "display": "IBM Granite 4.1 8B  (open-weight model)",
        "openrouter": "ibm-granite/granite-4.1-8b",
        "openai": None,
        "anthropic": None,
    },
}

LEVEL_DESCRIPTIONS: dict[int, str] = {
    1: "Direct HTTP  — stateless (no prior context sent to LLM)",
    2: "Direct HTTP  — full chat history in every request",
    3: "Pydantic AI  — system prompt + session/context management",
    4: "Pydantic AI  — ReAct loop with tools (web fetch, read folder, write output)",
    5: "Google ADK   — multi-agent orchestration with sub-agents",
}

# (label, rich style) per level
LEVEL_STYLE: dict[int, tuple[str, str]] = {
    1: ("LLM",            "bold cyan"),
    2: ("Chat",           "bold blue"),
    3: ("Chat Assistant", "bold green"),
    4: ("Tool Assistant", "bold magenta"),
    5: ("Agent",          "bold yellow"),
}

# ---------------------------------------------------------------------------
# Provider helpers
# ---------------------------------------------------------------------------

def get_available_providers() -> list[str]:
    providers = []
    if os.getenv("OPENROUTER_API_KEY"):
        providers.append("openrouter")
    if os.getenv("OPENAI_API_KEY"):
        providers.append("openai")
    if os.getenv("ANTHROPIC_API_KEY"):
        providers.append("anthropic")
    return providers


def detect_provider() -> Optional[str]:
    available = get_available_providers()
    return available[0] if available else None


def get_available_models(provider: str) -> list[str]:
    return [mid for mid, info in MODELS.items() if info.get(provider)]


def get_native_model(model_id: str, provider: str) -> Optional[str]:
    return MODELS.get(model_id, {}).get(provider)


def get_api_config(provider: str) -> dict:
    if provider == "openrouter":
        return {
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": os.getenv("OPENROUTER_API_KEY", ""),
        }
    if provider == "openai":
        return {
            "base_url": "https://api.openai.com/v1",
            "api_key": os.getenv("OPENAI_API_KEY", ""),
        }
    if provider == "anthropic":
        return {
            "base_url": "https://api.anthropic.com",
            "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
        }
    raise ValueError(f"Unknown provider: {provider}")


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    provider = detect_provider()
    model = None
    if provider:
        models = get_available_models(provider)
        model = models[0] if models else None
    return {"current_level": 1, "provider": provider, "model": model}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ---------------------------------------------------------------------------
# Streaming HTTP chat helper (levels 1 & 2)
# ---------------------------------------------------------------------------

_KEY_ENV_VARS = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai":     "OPENAI_API_KEY",
    "anthropic":  "ANTHROPIC_API_KEY",
}


def validate_api_key(provider: str, console) -> bool:
    """Return True if the API key env var for provider is set, else print help and return False."""
    env_var = _KEY_ENV_VARS.get(provider, "")
    if os.getenv(env_var):
        return True
    console.print(
        f"\n[bold red]No API key for '{provider}'.[/]  "
        f"Set [cyan]{env_var}[/] and retry:\n"
        f"  [dim]export {env_var}='your-key-here'[/]\n"
        f"Or use [cyan]/provider[/] to switch to a provider whose key is set."
    )
    return False


def stream_chat(
    messages: list[dict],
    provider: str,
    model_id: str,
    console,
    response_style: str = "cyan",
) -> str:
    """
    Stream a chat completion, printing tokens as they arrive.
    Reasoning tokens (DeepSeek R1) appear in dim italic.
    Returns the full response text.
    """
    import requests  # local import to keep startup fast

    if not validate_api_key(provider, console):
        return ""

    native_model = get_native_model(model_id, provider)
    if not native_model:
        console.print(f"[red]Model '{model_id}' is not available for provider '{provider}'[/]")
        return ""

    config = get_api_config(provider)
    collector: list[str] = []

    try:
        if provider == "anthropic":
            _stream_anthropic(messages, native_model, config, console, response_style, collector)
        else:
            _stream_openai_compat(messages, native_model, config, console, response_style, collector)
    except requests.exceptions.ConnectionError as exc:
        console.print(f"\n[bold red]Connection error:[/] {exc}")
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response else "?"
        try:
            body = exc.response.json()
            msg = body.get("error", {})
            if isinstance(msg, dict):
                msg = msg.get("message", str(body))
        except Exception:
            msg = exc.response.text[:300] if exc.response else str(exc)
        console.print(f"\n[bold red]HTTP {status}:[/] {msg}")
        if status == 401:
            env_var = _KEY_ENV_VARS.get(provider, "")
            console.print(f"  [dim]Check that [cyan]{env_var}[/] is correct.[/]")
    except Exception as exc:
        console.print(f"\n[bold red]Error:[/] {exc}")

    return "".join(collector)


def _stream_openai_compat(
    messages: list[dict],
    native_model: str,
    config: dict,
    console,
    style: str,
    collector: list[str],
) -> None:
    import requests, json as _json

    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }
    payload = {"model": native_model, "messages": messages, "stream": True}
    in_reasoning = False

    with requests.post(
        f"{config['base_url']}/chat/completions",
        headers=headers,
        json=payload,
        stream=True,
        timeout=120,
    ) as resp:
        resp.raise_for_status()
        for raw in resp.iter_lines():
            if not raw:
                continue
            line = raw.decode() if isinstance(raw, bytes) else raw
            if not line.startswith("data: "):
                continue
            data = line[6:]
            if data.strip() == "[DONE]":
                break
            try:
                chunk = _json.loads(data)
                delta = chunk["choices"][0]["delta"]

                # DeepSeek R1 and similar: surface reasoning tokens
                reasoning = delta.get("reasoning") or delta.get("reasoning_content") or ""
                if reasoning:
                    if not in_reasoning:
                        console.print("\n[dim italic]⟨thinking⟩[/]", end="")
                        in_reasoning = True
                    console.print(reasoning, end="", style="dim italic", markup=False, highlight=False)

                content = delta.get("content") or ""
                if content:
                    if in_reasoning:
                        console.print("\n[dim italic]⟨/thinking⟩[/]\n")
                        in_reasoning = False
                    console.print(content, end="", style=style, markup=False, highlight=False)
                    collector.append(content)
            except (_json.JSONDecodeError, KeyError, IndexError):
                pass

    if in_reasoning:
        console.print("\n[dim italic]⟨/thinking⟩[/]")
    console.print()  # trailing newline


def _stream_anthropic(
    messages: list[dict],
    native_model: str,
    config: dict,
    console,
    style: str,
    collector: list[str],
) -> None:
    import requests, json as _json

    headers = {
        "x-api-key": config["api_key"],
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    # Separate system message from user/assistant turns
    system_msg = ""
    chat_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_msg = msg["content"]
        else:
            chat_messages.append(msg)

    payload: dict = {
        "model": native_model,
        "max_tokens": 4096,
        "messages": chat_messages,
        "stream": True,
    }
    if system_msg:
        payload["system"] = system_msg

    with requests.post(
        f"{config['base_url']}/v1/messages",
        headers=headers,
        json=payload,
        stream=True,
        timeout=120,
    ) as resp:
        resp.raise_for_status()
        for raw in resp.iter_lines():
            if not raw:
                continue
            line = raw.decode() if isinstance(raw, bytes) else raw
            if not line.startswith("data: "):
                continue
            data = line[6:]
            try:
                event = _json.loads(data)
                if event.get("type") == "content_block_delta":
                    text = event["delta"].get("text", "")
                    if text:
                        console.print(text, end="", style=style, markup=False, highlight=False)
                        collector.append(text)
            except (_json.JSONDecodeError, KeyError):
                pass

    console.print()  # trailing newline


# ---------------------------------------------------------------------------
# Pydantic AI model builder (levels 3 & 4)
# ---------------------------------------------------------------------------

def build_pydantic_model(provider: str, model_id: str):
    """Return a pydantic-ai model instance for the given provider (pydantic-ai 0.8.x)."""
    env_var = _KEY_ENV_VARS.get(provider, "")
    if not os.getenv(env_var):
        raise ValueError(
            f"No API key for '{provider}'.  Set {env_var}=<your-key>"
        )
    native = get_native_model(model_id, provider)
    if not native:
        raise ValueError(f"Model '{model_id}' is not available for provider '{provider}'")

    config = get_api_config(provider)

    if provider == "anthropic":
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider
        prov = AnthropicProvider(api_key=config["api_key"])
        return AnthropicModel(native, provider=prov)
    else:
        # OpenAIChatModel uses the Chat Completions API — works with OpenRouter too
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider
        prov = OpenAIProvider(base_url=config["base_url"], api_key=config["api_key"])
        return OpenAIChatModel(native, provider=prov)


# ---------------------------------------------------------------------------
# Shared slash-command handler
# ---------------------------------------------------------------------------

# Return codes used when exiting to switch levels
_SWITCH_BASE = 10  # exit(10 + level) => switch to level N


def handle_slash(cmd: str, state: dict, console, level: int) -> str:
    """
    Process a slash command.  Returns:
      'continue'  — no change, stay in loop
      'rebuild'   — provider/model changed, caller should rebuild and reset history
      'clear'     — caller should clear history
      'exit'      — return to launcher

    /switch N calls sys.exit(10+N) directly.
    """
    parts = cmd.strip().split(maxsplit=1)
    slash = parts[0].lower()
    arg   = parts[1].strip() if len(parts) > 1 else ""

    if slash in ("/help", "/?"):
        print(
            "\nCommands:\n"
            "  /switch [1-5]    switch level (blank = list)\n"
            "  /provider [name] change provider (blank = list)\n"
            "  /model [name]    change model (blank = list)\n"
            "  /clear           clear conversation history\n"
            "  /exit            return to main menu\n"
        )
        return "continue"

    if slash == "/switch":
        if not arg:
            print("\nLevels:")
            for n, desc in LEVEL_DESCRIPTIONS.items():
                mark = ">" if n == level else " "
                print(f"  {mark} {n}  {desc}")
            print()
            return "continue"
        try:
            target = int(arg)
        except ValueError:
            print("Usage: /switch [1-5]")
            return "continue"
        if target not in range(1, 6):
            print("Level must be 1-5.")
            return "continue"
        state["current_level"] = target
        save_state(state)
        sys.exit(_SWITCH_BASE + target)

    if slash == "/provider":
        available = get_available_providers()
        if not arg:
            print("\nProviders:")
            for p in ["openrouter", "openai", "anthropic"]:
                mark   = ">" if p == state.get("provider") else " "
                status = "" if p in available else "  (no API key)"
                print(f"  {mark} {p}{status}")
            print()
            return "continue"
        if arg not in available:
            print(f"'{arg}' not available — check API key env var.")
            return "continue"
        state["provider"] = arg
        models = get_available_models(arg)
        state["model"] = models[0] if models else None
        save_state(state)
        print(f"Provider: {arg}  |  Model: {state['model']}")
        return "rebuild"

    if slash == "/model":
        if not arg:
            provider = state.get("provider", "")
            print(f"\nModels for {provider}:")
            for mid in get_available_models(provider):
                mark = ">" if mid == state.get("model") else " "
                print(f"  {mark} {mid}  {MODELS[mid]['display']}")
            print()
            return "continue"
        if arg not in MODELS:
            print(f"Unknown model '{arg}'.")
            return "continue"
        if not get_native_model(arg, state.get("provider", "")):
            print(f"'{arg}' not available for {state.get('provider')}.")
            return "continue"
        state["model"] = arg
        save_state(state)
        print(f"Model: {arg}")
        return "rebuild"

    if slash == "/clear":
        return "clear"

    if slash in ("/exit", "/quit", "/q"):
        return "exit"

    print(f"Unknown command '{slash}'. Type /help.")
    return "continue"
