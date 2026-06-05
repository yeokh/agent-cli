#!/usr/bin/env python3
"""
ADK Agent — Google Agent Development Kit file processor.

Reads instruction.md from inbox, processes files per those instructions,
writes output to outbox.  Supports Anthropic, OpenAI, and OpenRouter via
LiteLLM.  Call run_agent() from a background thread; it blocks until done,
calling log_callback for every log line produced.
"""

import asyncio
import logging
import os
import subprocess
from pathlib import Path
from typing import Callable

log = logging.getLogger("adk_agent")

# ─── Model Registry ──────────────────────────────────────────────────────────
# Each entry: model_key → {provider, display, litellm_id, env}
#   provider   : "anthropic" | "openai" | "openrouter"
#   display    : human-readable name shown in the UI
#   litellm_id : model string passed to LiteLlm()
#   env        : environment variable that must be set to use this model
MODELS: dict[str, dict] = {
    # ── Anthropic ────────────────────────────────────────────────────────────
    "claude-opus-4-5": {
        "provider":   "anthropic",
        "display":    "Claude Opus 4.5 (most capable)",
        "litellm_id": "claude-opus-4-5",
        "env":        "ANTHROPIC_API_KEY",
    },
    "claude-sonnet-4-6": {
        "provider":   "anthropic",
        "display":    "Claude Sonnet 4.6 (balanced)",
        "litellm_id": "claude-sonnet-4-6",
        "env":        "ANTHROPIC_API_KEY",
    },
    "claude-haiku-4-5-20251001": {
        "provider":   "anthropic",
        "display":    "Claude Haiku 4.5 (fast)",
        "litellm_id": "claude-haiku-4-5-20251001",
        "env":        "ANTHROPIC_API_KEY",
    },
    # ── OpenAI ───────────────────────────────────────────────────────────────
    "gpt-4o": {
        "provider":   "openai",
        "display":    "GPT-4o (most capable)",
        "litellm_id": "openai/gpt-4o",
        "env":        "OPENAI_API_KEY",
    },
    "gpt-4o-mini": {
        "provider":   "openai",
        "display":    "GPT-4o Mini (fast)",
        "litellm_id": "openai/gpt-4o-mini",
        "env":        "OPENAI_API_KEY",
    },
    # ── OpenRouter ───────────────────────────────────────────────────────────
    "openrouter/anthropic/claude-3-5-sonnet": {
        "provider":   "openrouter",
        "display":    "OR: Claude 3.5 Sonnet",
        "litellm_id": "openrouter/anthropic/claude-3-5-sonnet",
        "env":        "OPENROUTER_API_KEY",
    },
    "openrouter/anthropic/claude-3-7-sonnet": {
        "provider":   "openrouter",
        "display":    "OR: Claude 3.7 Sonnet",
        "litellm_id": "openrouter/anthropic/claude-3-7-sonnet",
        "env":        "OPENROUTER_API_KEY",
    },
    "openrouter/google/gemini-2.5-flash-preview-05-20": {
        "provider":   "openrouter",
        "display":    "OR: Gemini 2.5 Flash",
        "litellm_id": "openrouter/google/gemini-2.5-flash-preview-05-20",
        "env":        "OPENROUTER_API_KEY",
    },
    "openrouter/openai/gpt-4o": {
        "provider":   "openrouter",
        "display":    "OR: GPT-4o",
        "litellm_id": "openrouter/openai/gpt-4o",
        "env":        "OPENROUTER_API_KEY",
    },
    "openrouter/meta-llama/llama-4-maverick": {
        "provider":   "openrouter",
        "display":    "OR: Llama 4 Maverick",
        "litellm_id": "openrouter/meta-llama/llama-4-maverick",
        "env":        "OPENROUTER_API_KEY",
    },
}


def get_available_models() -> list[dict]:
    """Return models whose provider API key is present in the environment."""
    result = []
    for model_id, cfg in MODELS.items():
        if os.environ.get(cfg["env"]):
            result.append({
                "id":       model_id,
                "display":  cfg["display"],
                "provider": cfg["provider"],
            })
    return result


def default_model() -> str:
    """Pick the first available model, preferring Anthropic → OpenAI → OpenRouter."""
    for provider in ("anthropic", "openai", "openrouter"):
        for model_id, cfg in MODELS.items():
            if cfg["provider"] == provider and os.environ.get(cfg["env"]):
                return model_id
    return next(iter(MODELS))  # fallback to first key


# ─── Model Factory ────────────────────────────────────────────────────────────

def _build_model(model_id: str):
    """Return the appropriate ADK LiteLlm instance for *model_id*."""
    if model_id not in MODELS:
        raise ValueError(f"Unknown model: {model_id!r}")

    cfg      = MODELS[model_id]
    litellm  = cfg["litellm_id"]
    provider = cfg["provider"]

    from google.adk.models.lite_llm import LiteLlm  # noqa: PLC0415

    if provider == "openrouter":
        return LiteLlm(
            model=litellm,
            api_base="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        )

    # Anthropic and OpenAI: LiteLLM reads the key from the environment
    return LiteLlm(model=litellm)


# ─── Tools ───────────────────────────────────────────────────────────────────

def _make_tools(inbox: Path, outbox: Path) -> list:
    """Return tool functions bound to *inbox* and *outbox* paths."""

    inbox_r  = inbox.resolve()
    outbox_r = outbox.resolve()
    allowed  = (inbox_r, outbox_r)

    def _in_allowed(path: Path) -> bool:
        p = path.resolve()
        return any(str(p).startswith(str(a)) for a in allowed)

    def read_file(filepath: str) -> str:
        """Read a file from the inbox or outbox.

        Args:
            filepath: Path to the file.  May be absolute or relative to the
                      inbox directory.

        Returns:
            File contents as a string, or an error message.
        """
        candidates = [
            Path(filepath),
            inbox_r / filepath,
            outbox_r / filepath,
        ]
        for c in candidates:
            resolved = c.resolve()
            if _in_allowed(resolved) and resolved.is_file():
                try:
                    return resolved.read_text(encoding="utf-8")
                except Exception as exc:
                    return f"Error reading {filepath}: {exc}"
        return f"File not found: {filepath}"

    def write_file(filepath: str, content: str) -> str:
        """Write *content* to a file in the outbox directory.

        Args:
            filepath: Destination path.  May be absolute (must be inside
                      outbox) or relative (resolved against outbox).
            content:  Text content to write.

        Returns:
            Confirmation message or error.
        """
        abs_path = Path(filepath).resolve()
        if str(abs_path).startswith(str(outbox_r)):
            target = abs_path
        else:
            target = (outbox_r / filepath).resolve()
            if not str(target).startswith(str(outbox_r)):
                return f"Path traversal denied: {filepath}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Wrote {target.stat().st_size} bytes → {target.relative_to(outbox_r)}"

    def list_files(directory: str = "inbox") -> str:
        """List files in inbox or outbox.

        Args:
            directory: "inbox" or "outbox" (or their absolute paths).

        Returns:
            Newline-separated list of relative paths and sizes.
        """
        if directory in ("inbox", str(inbox_r)):
            base = inbox_r
            label = "inbox"
        elif directory in ("outbox", str(outbox_r)):
            base = outbox_r
            label = "outbox"
        else:
            return f"Unknown directory '{directory}'. Use 'inbox' or 'outbox'."
        if not base.exists():
            return f"{label} does not exist."
        files = sorted(base.rglob("*"))
        rows  = [
            f"{p.relative_to(base)}  ({p.stat().st_size} bytes)"
            for p in files if p.is_file()
        ]
        return "\n".join(rows) if rows else f"{label} is empty."

    def run_bash(command: str) -> str:
        """Execute a bash command in the project root directory.

        Use this for tasks like extracting archives, converting files, or
        running scripts.  The working directory is the parent of inbox/outbox.

        Args:
            command: Shell command to run.

        Returns:
            Combined stdout + stderr, or an error message.
        """
        blocked = ["rm -rf /", "dd if=", "mkfs", ":(){ :|:& };:"]
        for b in blocked:
            if b in command:
                return f"Command blocked (contains '{b}')"
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(inbox_r.parent),
            )
            output = (result.stdout + result.stderr).strip()
            return output or f"Exit code {result.returncode}"
        except subprocess.TimeoutExpired:
            return "Command timed out (60 s)"
        except Exception as exc:
            return f"Error: {exc}"

    return [read_file, write_file, list_files, run_bash]


# ─── Event Formatter ─────────────────────────────────────────────────────────

def _format_event(event) -> list[str]:
    """Convert a single ADK Event into zero or more log lines."""
    lines: list[str] = []
    try:
        content = getattr(event, "content", None)
        if content is None:
            return lines
        author = getattr(event, "author", "model")
        parts  = getattr(content, "parts", None) or []

        for part in parts:
            # ── Plain text ──────────────────────────────────────────────────
            text = getattr(part, "text", None)
            if text and text.strip():
                prefix = "[assistant]" if author != "user" else "[user]"
                for line in text.strip().split("\n"):
                    if line.strip():
                        lines.append(f"{prefix} {line}")

            # ── Tool call ───────────────────────────────────────────────────
            fc = getattr(part, "function_call", None)
            if fc:
                name     = getattr(fc, "name", "?")
                raw_args = getattr(fc, "args", {}) or {}
                args_str = ", ".join(
                    f"{k}={repr(str(v))[:60]}" for k, v in dict(raw_args).items()
                )
                lines.append(f"[tool_use] {name}({args_str})")

            # ── Tool response ───────────────────────────────────────────────
            fr = getattr(part, "function_response", None)
            if fr:
                name = getattr(fr, "name", "?")
                resp = getattr(fr, "response", {})
                if isinstance(resp, dict):
                    resp_str = str(resp.get("result", resp))[:300]
                else:
                    resp_str = str(resp)[:300]
                lines.append(f"[result] {name}: {resp_str}")

    except Exception as exc:
        lines.append(f"[meta] event parse error: {exc}")

    return lines


# ─── System Prompt ────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a file-processing agent. Follow these steps every run:

1. Read instruction.md from the inbox to understand your task.
2. List the inbox files to discover what needs processing.
3. Process each relevant file according to the instructions.
4. Write all output files to the outbox directory.
5. Write a concise processing summary to outbox/agent.log.

Constraints:
- Only read from inbox and write to outbox.
- If the inbox contains a .tar or .zip archive, extract it first (run_bash).
- Do not invent data; base output strictly on the input files.
"""


# ─── Async Runner ────────────────────────────────────────────────────────────

async def _run_async(
    model_id: str,
    inbox: Path,
    outbox: Path,
    log_callback: Callable[[str], None],
) -> None:
    """Create and drive the ADK agent, emitting log lines via *log_callback*."""
    from google.adk.agents import LlmAgent          # noqa: PLC0415
    from google.adk.runners import InMemoryRunner   # noqa: PLC0415
    from google.genai import types as genai_types   # noqa: PLC0415

    model  = _build_model(model_id)
    tools  = _make_tools(inbox, outbox)

    agent  = LlmAgent(
        name="file_processor",
        model=model,
        instruction=_SYSTEM_PROMPT,
        tools=tools,
    )

    runner  = InMemoryRunner(agent=agent, app_name="adk_agent")
    session = await runner.session_service.create_session(
        app_name="adk_agent",
        user_id="run_user",
    )

    prompt = (
        f"Read {inbox}/instruction.md for your task, then execute it fully. "
        f"Input files are in {inbox}/. "
        f"Write all outputs (including agent.log summary) to {outbox}/. "
        f"Do not access paths outside {inbox}/ and {outbox}/."
    )

    user_message = genai_types.Content(
        role="user",
        parts=[genai_types.Part.from_text(text=prompt)],
    )

    log_callback(f"model={model_id}  inbox={inbox}  outbox={outbox}")

    async for event in runner.run_async(
        user_id="run_user",
        session_id=session.id,
        new_message=user_message,
    ):
        for line in _format_event(event):
            log_callback(line)


# ─── Public Sync API ──────────────────────────────────────────────────────────

def run_agent(
    model_id: str,
    inbox: Path,
    outbox: Path,
    log_callback: Callable[[str], None],
) -> None:
    """Run the ADK agent synchronously (blocks until complete).

    Intended to be called from a background daemon thread started by
    web_app.py.  Raises on fatal errors; the caller is responsible for
    catching and recording them.

    Args:
        model_id:     Key from MODELS (e.g. "claude-sonnet-4-6").
        inbox:        Absolute path to the inbox directory.
        outbox:       Absolute path to the outbox directory.
        log_callback: Called with each log line as it is produced.
    """
    asyncio.run(_run_async(model_id, inbox, outbox, log_callback))
