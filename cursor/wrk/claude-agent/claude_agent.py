#!/usr/bin/env python3
"""
Claude Agent — Claude Agent SDK file processor.

Reads instruction.md from inbox, processes files per those instructions,
writes output to outbox. Supports Anthropic, OpenAI, and OpenRouter models
via the Claude Agent SDK. OpenAI/OpenRouter requests are routed through an
Anthropic-format gateway (e.g. LiteLLM) configured with GATEWAY_URL.

Architecture
────────────
  web_app.py   → run_agent()           → Claude Agent SDK query()
               → _build_sdk_options()  → ClaudeAgentOptions + hooks
               → stream events         → log_callback (AgentState)
                                                ↓
                                     Flask SSE → browser terminal

Workshop exercises that touch this file:
  Exercise 01 — Explore        : read _registry, run_agent, hooks
  Exercise 03 — Add Tool       : discuss built-in tools vs MCP tools
  Exercise 05 — Custom Toolsets: add custom MCP tool server
  Exercise 06 — Multi-Agent    : run_agent() sequentially for pipelines
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from pathlib import Path
from typing import Callable

import httpx

from claude_agent_sdk import ClaudeAgentOptions, HookMatcher, query
from claude_agent_sdk.types import ResultMessage, StreamEvent

log = logging.getLogger("claude_agent")


# ─── Dynamic Model Registry ──────────────────────────────────────────────────
#
# WORKSHOP (Exercise 01 — Explore)
# ─────────────────────────────────
# Models are fetched live from provider APIs. This lets the UI display real,
# up-to-date model IDs instead of hardcoding them. OpenAI and OpenRouter models
# are routed through an Anthropic-format gateway (LiteLLM) by prefixing
# "openai/" or "openrouter/" to the model ID (same convention as LiteLLM).

_registry_lock: threading.Lock = threading.Lock()
_registry_cache: list[dict] | None = None


def _fetch_anthropic_models() -> list[dict]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return []
    try:
        r = httpx.get(
            "https://api.anthropic.com/v1/models",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
            timeout=10,
        )
        r.raise_for_status()
        entries = r.json().get("data", [])
        result = [
            {
                "id":       m["id"],
                "provider": "anthropic",
                "display":  m.get("display_name", m["id"]),
                "model_id": m["id"],
                "env":      "ANTHROPIC_API_KEY",
            }
            for m in entries
        ]
        result.sort(key=lambda x: x["id"])
        return result
    except Exception as exc:
        log.warning("Failed to fetch Anthropic models: %s", exc)
        return []


def _fetch_openai_models() -> list[dict]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return []
    try:
        r = httpx.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        r.raise_for_status()
        entries = r.json().get("data", [])
        gpt = sorted([m for m in entries if m["id"].startswith("gpt-")], key=lambda m: m["id"])
        return [
            {
                "id":       f"openai/{m['id']}",
                "provider": "openai",
                "display":  m["id"],
                "model_id": f"openai/{m['id']}",
                "env":      "OPENAI_API_KEY",
            }
            for m in gpt
        ]
    except Exception as exc:
        log.warning("Failed to fetch OpenAI models: %s", exc)
        return []


def _fetch_openrouter_models() -> list[dict]:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return []
    try:
        r = httpx.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
        r.raise_for_status()
        entries = r.json().get("data", [])
        text_models = sorted(
            [
                m for m in entries
                if m.get("architecture", {}).get("modality", "").endswith("->text")
            ],
            key=lambda m: m["id"],
        )
        return [
            {
                "id":       f"openrouter/{m['id']}",
                "provider": "openrouter",
                "display":  f"OR: {m.get('name', m['id'])}",
                "model_id": f"openrouter/{m['id']}",
                "env":      "OPENROUTER_API_KEY",
            }
            for m in text_models
        ]
    except Exception as exc:
        log.warning("Failed to fetch OpenRouter models: %s", exc)
        return []


def _registry() -> list[dict]:
    global _registry_cache
    if _registry_cache is None:
        with _registry_lock:
            if _registry_cache is None:
                log.info("Loading model registry from provider APIs…")
                _registry_cache = (
                    _fetch_anthropic_models()
                    + _fetch_openai_models()
                    + _fetch_openrouter_models()
                )
                log.info("Model registry loaded: %d models", len(_registry_cache))
    return _registry_cache


def _get_model_cfg(model_key: str) -> dict | None:
    return next((m for m in _registry() if m["id"] == model_key), None)


def get_available_models() -> list[dict]:
    """Return all models from configured providers."""
    return [
        {"id": m["id"], "display": m["display"], "provider": m["provider"]}
        for m in _registry()
    ]


def default_model() -> str:
    """Pick the first available model, preferring Anthropic → OpenAI → OpenRouter."""
    for provider in ("anthropic", "openai", "openrouter"):
        for m in _registry():
            if m["provider"] == provider:
                return m["id"]
    reg = _registry()
    return reg[0]["id"] if reg else ""


# ─── SDK Option Builder ──────────────────────────────────────────────────────
#
# WORKSHOP (Exercise 01 — Explore)
# ─────────────────────────────────
# The Claude Agent SDK uses a single options object to control tools, model,
# permissions, and hook callbacks. For OpenAI/OpenRouter, we set an
# Anthropic-format gateway URL and pass the provider API key as the auth token.

def _build_sdk_options(model_key: str, inbox: Path, outbox: Path, log_callback: Callable[[str], None]) -> ClaudeAgentOptions:
    cfg = _get_model_cfg(model_key)
    if cfg is None:
        raise ValueError(f"Unknown model: {model_key!r}")

    project_root = inbox.parent.resolve()
    allowed = (inbox.resolve(), outbox.resolve())

    def _resolve_path(raw: str | None) -> Path | None:
        if not raw:
            return None
        p = Path(raw)
        if not p.is_absolute():
            p = project_root / p
        return p.resolve()

    def _in_allowed(path: Path | None, *, outbox_only: bool = False) -> bool:
        if path is None:
            return False
        if outbox_only:
            return str(path).startswith(str(allowed[1]))
        return any(str(path).startswith(str(base)) for base in allowed)

    def _format_kv(args: dict) -> str:
        parts = []
        for key, value in args.items():
            snippet = repr(value)
            if len(snippet) > 80:
                snippet = snippet[:77] + "..."
            parts.append(f"{key}={snippet}")
        return ", ".join(parts)

    async def pre_tool_use(input_data, tool_use_id, context):
        tool = input_data.get("tool_name", "")
        args = input_data.get("tool_input", {}) or {}
        log_callback(f"[tool_use] {tool}({_format_kv(args)})")

        # Enforce path boundaries on file operations.
        if tool in {"Read", "Edit", "Write"}:
            path = _resolve_path(args.get("file_path"))
            outbox_only = tool == "Write"
            if not _in_allowed(path, outbox_only=outbox_only):
                return {
                    "hookSpecificOutput": {
                        "hookEventName": input_data["hook_event_name"],
                        "permissionDecision": "deny",
                        "permissionDecisionReason": "Path outside inbox/outbox",
                    }
                }

        if tool in {"Glob", "Grep"}:
            path = _resolve_path(args.get("path"))
            if path is None:
                # Default to inbox if no path is provided.
                updated = dict(args)
                updated["path"] = str(inbox)
                return {
                    "hookSpecificOutput": {
                        "hookEventName": input_data["hook_event_name"],
                        "permissionDecision": "allow",
                        "updatedInput": updated,
                    }
                }
            if not _in_allowed(path):
                return {
                    "hookSpecificOutput": {
                        "hookEventName": input_data["hook_event_name"],
                        "permissionDecision": "deny",
                        "permissionDecisionReason": "Path outside inbox/outbox",
                    }
                }

        if tool == "Bash":
            command = str(args.get("command", ""))
            blocked = ["rm -rf /", "dd if=", "mkfs", ":(){ :|:& };:", "sudo "]
            for b in blocked:
                if b in command:
                    return {
                        "hookSpecificOutput": {
                            "hookEventName": input_data["hook_event_name"],
                            "permissionDecision": "deny",
                            "permissionDecisionReason": f"Blocked bash pattern: {b}",
                        }
                    }

        return {}

    async def post_tool_use(input_data, tool_use_id, context):
        tool = input_data.get("tool_name", "")
        result = input_data.get("tool_output", "")
        snippet = str(result)
        if len(snippet) > 300:
            snippet = snippet[:297] + "..."
        log_callback(f"[result] {tool}: {snippet}")
        return {}

    async def post_tool_failure(input_data, tool_use_id, context):
        tool = input_data.get("tool_name", "")
        error = input_data.get("error", "")
        log_callback(f"[result] {tool}: ERROR {error}")
        return {}

    env = {}
    if cfg["provider"] in {"openai", "openrouter"}:
        gateway_url = os.environ.get("GATEWAY_URL") or os.environ.get("ANTHROPIC_BASE_URL", "")
        if not gateway_url:
            raise RuntimeError("GATEWAY_URL or ANTHROPIC_BASE_URL is required for OpenAI/OpenRouter models")
        env = {
            "ANTHROPIC_BASE_URL": gateway_url,
            "ANTHROPIC_AUTH_TOKEN": os.environ.get(cfg["env"], ""),
        }

    # WORKSHOP (Exercise 03 — Add Tool)
    # ───────────────────────────────────
    # To add a custom MCP tool, register your server here and include its
    # tool names in allowed_tools (e.g. "mcp__custom__word_count").
    #
    # WORKSHOP (Exercise 05 — Custom Toolsets)
    # ─────────────────────────────────────────
    # Import additional MCP servers from tools/ modules and merge them into
    # the mcp_servers dict below.

    return ClaudeAgentOptions(
        model=cfg["model_id"],
        cwd=str(project_root),
        system_prompt=_SYSTEM_PROMPT,
        permission_mode="dontAsk",
        allowed_tools=["Read", "Write", "Edit", "Glob", "Grep", "Bash"],
        include_partial_messages=True,
        env=env,
        hooks={
            "PreToolUse": [HookMatcher(hooks=[pre_tool_use])],
            "PostToolUse": [HookMatcher(hooks=[post_tool_use])],
            "PostToolUseFailure": [HookMatcher(hooks=[post_tool_failure])],
        },
    )


# ─── System Prompt ───────────────────────────────────────────────────────────
#
# WORKSHOP (Exercise 01 — Explore)
# ─────────────────────────────────
# The system prompt is the agent's standing instruction. The task-specific
# instructions live in inbox/instruction.md and are read at runtime.

_SYSTEM_PROMPT = """\
You are a file-processing agent powered by the Claude Agent SDK. Follow these steps:

1. Call Glob or Read to discover what payload files are available.
2. Read instruction.md to understand your task.
3. Process each relevant payload file according to those instructions.
4. Write all output files to the outbox directory using Write.
5. Write a concise processing summary to outbox/agent.log.

Guidelines:
- Only read from inbox; only write to outbox.
- If the inbox contains a .tar or .zip archive, extract it with Bash before processing.
- When a task requires computation (sorting, aggregating, parsing CSV), prefer
  Bash with a Python one-liner over doing it in your reasoning.
- Do not invent data; base all output strictly on the input files.
- Confirm each Write call succeeded before moving to the next file.
"""


# ─── Streaming Helpers ───────────────────────────────────────────────────────

def _emit_lines(log_callback: Callable[[str], None], text: str) -> None:
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped:
            log_callback(f"[assistant] {stripped}")


async def _run_agent_async(
    model_key: str,
    inbox: Path,
    outbox: Path,
    log_callback: Callable[[str], None],
) -> None:
    options = _build_sdk_options(model_key, inbox, outbox, log_callback)
    prompt = (
        f"Read {inbox}/instruction.md for your task, then execute it fully. "
        f"Input files are in {inbox}/. "
        f"Write all outputs (including agent.log summary) to {outbox}/. "
        f"Do not access paths outside {inbox}/ and {outbox}/."
    )

    buffer: list[str] = []

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, StreamEvent):
            event = message.event
            if event.get("type") == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    chunk = delta.get("text", "")
                    if chunk:
                        buffer.append(chunk)
                        joined = "".join(buffer)
                        if "\n" in joined:
                            lines = joined.split("\n")
                            for line in lines[:-1]:
                                if line.strip():
                                    log_callback(f"[assistant] {line.strip()}")
                            buffer.clear()
                            if lines[-1]:
                                buffer.append(lines[-1])
        elif isinstance(message, ResultMessage):
            if buffer:
                _emit_lines(log_callback, "".join(buffer))
                buffer.clear()
            if message.result:
                _emit_lines(log_callback, str(message.result))


# ─── Public Synchronous API ──────────────────────────────────────────────────
#
# WORKSHOP (Exercise 06 — Multi-Agent Pipeline)
# ──────────────────────────────────────────────
# run_agent() is synchronous so it can be called from a threading.Thread in
# web_app.py without extra asyncio wiring.

def run_agent(
    model_key: str,
    inbox: Path,
    outbox: Path,
    log_callback: Callable[[str], None],
) -> None:
    """Run the Claude Agent SDK loop synchronously (blocks until complete)."""
    log_callback(f"model={model_key}  inbox={inbox}  outbox={outbox}")
    asyncio.run(_run_agent_async(model_key, inbox, outbox, log_callback))
