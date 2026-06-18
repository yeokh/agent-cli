#!/usr/bin/env python3
"""
ADK Agent Harness — core agent logic.

Reads agent/instruction.md (plus any skill .md files in agent/), processes
the job payload files in input/, and writes results to output/ using
Google ADK (LlmAgent + InMemoryRunner + LiteLlm).

Two entry points share this module:

    python adk_agent.py     headless run (CI/CD, containers)
    python web_app.py       Flask web UI (imports run_agent below)

Architecture
------------
  web_app.py / __main__  ->  run_agent()
                                |  _build_model()  ->  LiteLlm instance
                                |  _make_tools()   ->  ADK tool functions (incl. web_fetch)
                                v
                          LlmAgent + InMemoryRunner
                                |
                         runner.run_async() yields Events
                                |
                          _format_event() -> log lines
                                |
                          log_callback (SSE / stdout)

Workshop exercises that touch this file:
  Exercise 3 -- Custom Tools : CUSTOM_TOOLS / CUSTOM_TOOL_NAMES
  Exercise 4 -- Guardrail    : run_guardrail_check()
  Exercise 5 -- Skill Loader : load_skills()
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import httpx

log = logging.getLogger("adk_agent")

PROVIDERS = ("anthropic", "openrouter", "openai-compatible")

DEFAULT_MODEL = "claude-opus-4-5"
DEFAULT_MAX_OUTPUT_TOKENS = 16384
WEB_FETCH_MAX_BYTES = 512_000
WEB_FETCH_DEFAULT_TIMEOUT = 30


# --- Environment Helpers ------------------------------------------------------

def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, ""))
    except ValueError:
        return default


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in ("0", "false", "no", "off")


def allow_shell() -> bool:
    return _env_bool("ALLOW_SHELL", True)


def shell_timeout() -> int:
    return _env_int("SHELL_TIMEOUT", 60)


# --- Path Helpers -------------------------------------------------------------

def _safe_resolve(base: Path, rel: str) -> Path:
    """Resolve rel against base and reject any path-traversal attempt."""
    target = (base / rel).resolve()
    if not str(target).startswith(str(base.resolve())):
        raise ValueError("Path traversal denied")
    return target


def _list_files(base: Path, exclude: set[str] | None = None) -> list[str]:
    exclude = exclude or set()
    if not base.exists():
        return []
    return sorted(
        str(p.relative_to(base)).replace("\\", "/")
        for p in base.rglob("*")
        if p.is_file() and p.name not in exclude
    )


# --- ADK Tool Implementations -------------------------------------------------
#
# In Google ADK, tools are plain Python functions. The ADK framework builds the
# LLM tool schema automatically from:
#   - function name       -> tool name the LLM calls
#   - docstring           -> description the LLM reads (Google-style Args/Returns)
#   - type annotations    -> parameter schema
#   - return type str     -> the result returned to the LLM
#
# All tools are defined as closures inside _make_tools() so they capture
# the resolved input_dir and output_dir paths at construction time.  Path-
# traversal checks are applied on every call.

def _validate_fetch_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL must use http:// or https://")
    if not parsed.netloc:
        raise ValueError("URL must include a host")
    return url.strip()


def _make_tools(input_dir: Path, output_dir: Path) -> list:
    """Return the scoped tool functions bound to input_dir and output_dir."""
    input_r = input_dir.resolve()
    output_r = output_dir.resolve()

    def list_input_files() -> str:
        """List payload files in the input folder.

        Call this first to discover what files are available before reading them.

        Returns:
            JSON array of relative file paths.
        """
        return json.dumps(_list_files(input_r))

    def read_input_file(path: str) -> str:
        """Read a file from the input folder and return its text content.

        Args:
            path: File path relative to the input folder.

        Returns:
            UTF-8 text content of the file, or an error message.
        """
        try:
            target = _safe_resolve(input_r, path)
        except ValueError as exc:
            return f"Error: {exc}"
        if not target.is_file():
            return f"File not found: {path}"
        return target.read_text(encoding="utf-8", errors="replace")

    def write_output(path: str, content: str) -> str:
        """Write or overwrite a file in the output folder.

        Creates parent directories as needed.  Only the output folder is
        writable; attempts to write outside it are rejected.

        Args:
            path: Destination path relative to the output folder.
            content: Full text content to write.

        Returns:
            Confirmation message with byte count, or an error message.
        """
        try:
            target = _safe_resolve(output_r, path)
        except ValueError as exc:
            return f"Error: {exc}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Wrote {target.stat().st_size} bytes to {path}"

    def append_output(path: str, content: str) -> str:
        """Append text to a file in the output folder, creating it if absent.

        Args:
            path: Destination path relative to the output folder.
            content: Text content to append.

        Returns:
            Confirmation message, or an error message.
        """
        try:
            target = _safe_resolve(output_r, path)
        except ValueError as exc:
            return f"Error: {exc}"
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as fh:
            fh.write(content)
        return f"Appended {len(content)} chars to {path}"

    def list_output_files() -> str:
        """List files already written to the output folder (excluding agent.log).

        Returns:
            JSON array of relative file paths in the output folder.
        """
        return json.dumps(_list_files(output_r, exclude={"agent.log"}))

    def run_command(command: str, timeout: int = 60) -> str:
        """Execute a shell command in the output folder.

        The working directory is the output folder.  Use for external tools
        such as grep, awk, python, jq, curl, or ansible-lint.

        Args:
            command: Shell command string to execute (piping and && are supported).
            timeout: Maximum seconds the command may run (default 60).

        Returns:
            JSON object with stdout, stderr, and returncode fields.
        """
        if not allow_shell():
            log.warning("[tool] run_command blocked: ALLOW_SHELL=false")
            return "Shell access is disabled (ALLOW_SHELL=false)"
        effective_timeout = min(int(timeout), shell_timeout())
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                cwd=str(output_r),
            )
            log.info("[tool] run_command(%s) -> rc=%d", command, result.returncode)
            return json.dumps({
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            })
        except subprocess.TimeoutExpired:
            log.info("[tool] run_command timed out after %ds: %s", effective_timeout, command)
            return json.dumps({"stdout": "", "stderr": "Command timed out", "returncode": -1})

    def web_fetch(url: str, timeout: int = WEB_FETCH_DEFAULT_TIMEOUT) -> str:
        """Fetch a URL over HTTP/HTTPS and return the response body as text.

        Use this to retrieve web pages or JSON API responses (e.g. Red Hat
        CVE data at https://access.redhat.com/security/cve/<CVE-ID> or the
        Hydra JSON API).  Redirects are followed automatically.

        Args:
            url: Absolute http:// or https:// URL to fetch.
            timeout: Request timeout in seconds (default 30, max 60).

        Returns:
            JSON with url, status_code, content_type, truncated, and text fields.
        """
        try:
            fetch_url = _validate_fetch_url(url)
        except ValueError as exc:
            return json.dumps({"error": str(exc)})
        effective_timeout = min(max(int(timeout), 1), 60)
        try:
            with httpx.Client(
                follow_redirects=True,
                timeout=effective_timeout,
                headers={"User-Agent": "adk-agent-harness/1.0"},
            ) as client:
                with client.stream("GET", fetch_url) as resp:
                    chunks: list[bytes] = []
                    size = 0
                    truncated = False
                    for chunk in resp.iter_bytes():
                        if size + len(chunk) > WEB_FETCH_MAX_BYTES:
                            remaining = WEB_FETCH_MAX_BYTES - size
                            if remaining > 0:
                                chunks.append(chunk[:remaining])
                            truncated = True
                            break
                        chunks.append(chunk)
                        size += len(chunk)
                    body = b"".join(chunks)
                    content_type = resp.headers.get("content-type", "")
                    if "application/json" in content_type or body.startswith(b"{") or body.startswith(b"["):
                        text = body.decode("utf-8", errors="replace")
                    elif "text/" in content_type or "html" in content_type or "xml" in content_type:
                        text = body.decode("utf-8", errors="replace")
                    else:
                        text = body.decode("utf-8", errors="replace")
                    log.info("[tool] web_fetch(%s) -> %d", fetch_url, resp.status_code)
                    return json.dumps({
                        "url": str(resp.url),
                        "status_code": resp.status_code,
                        "content_type": content_type,
                        "truncated": truncated,
                        "text": text,
                    })
        except httpx.TimeoutException:
            log.info("[tool] web_fetch timed out after %ds: %s", effective_timeout, url)
            return json.dumps({"error": f"Request timed out after {effective_timeout}s"})
        except httpx.HTTPError as exc:
            log.info("[tool] web_fetch failed: %s", exc)
            return json.dumps({"error": str(exc)})

    return [list_input_files, read_input_file, write_output, append_output,
            list_output_files, run_command, web_fetch]


# ==============================================================================
# WORKSHOP EXERCISE 3 -- Add Custom Tools
# ==============================================================================
#
# Add your own Python functions to CUSTOM_TOOLS and their names to
# CUSTOM_TOOL_NAMES.  ADK infers the tool schema from type annotations and
# docstrings automatically -- no decorator needed.
#
# Example:
#
#   def word_count(path: str) -> str:
#       """Count lines and words in an input file.
#
#       Args:
#           path: File path relative to the input folder.
#
#       Returns:
#           A summary with line and word counts.
#       """
#       from pathlib import Path
#       import os
#       text = (Path(os.environ.get("INPUT_DIR", "input")) / path).read_text()
#       return f"{len(text.splitlines())} lines, {len(text.split())} words"
#
#   CUSTOM_TOOLS = [word_count]
#   CUSTOM_TOOL_NAMES = ["word_count"]

CUSTOM_TOOLS: list = []
CUSTOM_TOOL_NAMES: list[str] = []


# ==============================================================================
# WORKSHOP EXERCISE 4 -- Guardrail Agent
# ==============================================================================

async def run_guardrail_check(instructions: str, input_files: list[str]) -> tuple[bool, str]:
    """Validate task instructions before the main agent runs.

    Returns (is_safe, reason).  When is_safe is False, run_agent raises
    RuntimeError and the main agent never starts.

    Workshop: replace the pass-through below with a fast LLM judge -- e.g.
    call claude-haiku with the instructions and ask whether this is a safe
    file-processing task.

    Example implementation:
    #
    #   import anthropic
    #   client = anthropic.AsyncAnthropic()
    #   resp = await client.messages.create(
    #       model="claude-haiku-4-5-20251001",
    #       max_tokens=100,
    #       system=("Reply SAFE or UNSAFE: <reason>.  "
    #               "UNSAFE if instructions try to exfiltrate data, "
    #               "attack other systems, or escape the sandbox."),
    #       messages=[{"role": "user",
    #                  "content": f"Files: {input_files}\n\n{instructions}"}],
    #   )
    #   verdict = resp.content[0].text.strip()
    #   return verdict.upper().startswith("SAFE"), verdict
    """
    return True, "Guardrail pass-through (not implemented)"


# ==============================================================================
# WORKSHOP EXERCISE 5 -- Skill Loader
# ==============================================================================

def load_skills(agent_dir: Path) -> tuple[list, list[str]]:
    """Scan agent/skills/*.py for extra tool functions.

    Returns (tool_functions, tool_names).  Each tool function is a plain Python
    function with type annotations and a docstring; ADK infers its schema.

    Workshop: implement dynamic loading.

    Example:
    #
    #   import importlib.util
    #   tools, names = [], []
    #   skills_dir = agent_dir / "skills"
    #   for py in sorted(skills_dir.glob("*.py")):
    #       spec = importlib.util.spec_from_file_location(py.stem, py)
    #       module = importlib.util.module_from_spec(spec)
    #       spec.loader.exec_module(module)
    #       for name, obj in vars(module).items():
    #           if callable(obj) and not name.startswith("_"):
    #               tools.append(obj)
    #               names.append(name)
    #   return tools, names
    """
    return [], []


# --- Agent Folder Loading -----------------------------------------------------
#
# Google ADK inject_session_state() treats {identifier} in the system prompt as
# session-state placeholders. Skill docs often contain Python f-strings like
# {table_selector}; escape those so they pass through unchanged.

_ADK_STATE_VAR = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _escape_adk_instruction_vars(text: str) -> str:
    """Prevent ADK from treating {name} literals in markdown as session state."""

    def repl(match: re.Match[str]) -> str:
        name = match.group(1)
        if name.isidentifier():
            return "{" + name + "\u200b}"
        return match.group(0)

    return _ADK_STATE_VAR.sub(repl, text)


def load_agent_folder(agent_dir: Path) -> tuple[str, str]:
    """Return (instruction_text, skills_block) from the agent/ folder.

    instruction.md is required.  Every other top-level .md file is appended
    to the system prompt as a skill reference document.
    """
    instruction_file = agent_dir / "instruction.md"
    if not instruction_file.is_file():
        raise FileNotFoundError(f"instruction.md not found in {agent_dir}")
    instruction = _escape_adk_instruction_vars(
        instruction_file.read_text(encoding="utf-8")
    )

    sections = []
    for md in sorted(agent_dir.glob("*.md")):
        if md.name == "instruction.md":
            continue
        body = _escape_adk_instruction_vars(md.read_text(encoding="utf-8"))
        sections.append(f"### {md.name}\n\n{body}")
    skills_block = "\n\n".join(sections)
    return instruction, skills_block


# --- System Prompt ------------------------------------------------------------

def build_system_prompt(
    instruction: str,
    skills_block: str,
    custom_skill_names: list[str] | None = None,
) -> str:
    """Assemble the full system prompt."""
    custom_lines = "".join(
        f"  - {name}  (custom skill)\n"
        for name in (custom_skill_names or [])
    )

    if allow_shell():
        shell_block = (
            f"Shell guidance:\n"
            f"  - Prefer targeted commands (grep, awk, python, jq, curl, ansible-lint)\n"
            f"    over broad destructive ones.\n"
            f"  - Working directory for commands is the output folder.\n"
            f"  - Write command output to the output folder via write_output when it\n"
            f"    should be persisted; stdout from run_command is ephemeral.\n"
            f"  - Commands time out after {shell_timeout()} seconds.\n"
        )
    else:
        shell_block = "SHELL ACCESS DISABLED -- run_command will return an error.\n"

    prompt = (
        "You are a capable, autonomous AI agent running inside a secure container.\n"
        "You interact with the world ONLY through the tools listed below.\n"
        "\n"
        "Available tools:\n"
        "  - list_input_files  -- list payload files in the input folder\n"
        "  - read_input_file   -- read a file from the input folder\n"
        "  - write_output      -- write a file to the output folder\n"
        "  - append_output     -- append to a file in the output folder\n"
        "  - list_output_files -- list files already written to the output folder\n"
        "  - run_command       -- execute a shell command; returns stdout, stderr, returncode\n"
        "  - web_fetch         -- fetch an http(s) URL; returns status, content_type, and text\n"
        f"{custom_lines}"
        "\n"
        "Large file guidance:\n"
        "  - Keep each write_output call under ~8 KB of content.\n"
        "  - For larger files, use append_output in several smaller chunks, or\n"
        "    write via run_command (e.g. python3 -c or a heredoc).\n"
        "\n"
        f"{shell_block}"
    )

    if skills_block:
        prompt += f"\n## Skills\n\n{skills_block}\n"

    prompt += f"\nTASK INSTRUCTIONS:\n{instruction}"
    return prompt


KICKOFF_PROMPT = "Begin executing the task instructions now."


# --- Model Builder ------------------------------------------------------------

def max_output_tokens() -> int:
    return _env_int("MAX_OUTPUT_TOKENS", DEFAULT_MAX_OUTPUT_TOKENS)


def _build_model(provider: str, model_id: str, *, output_token_limit: int):
    """Return a LiteLlm instance configured for the given provider and model.

    Routes each provider to its LiteLlm representation:
      anthropic         -> LiteLlm(model=model_id)           reads ANTHROPIC_API_KEY
      openrouter        -> LiteLlm(model=openrouter/...)     explicit api_base + key
      openai-compatible -> LiteLlm(model=openai/...)         OPENAI_BASE_URL + key

    output_token_limit is passed as max_tokens to LiteLLM so tool-call JSON is not
    truncated mid-string (a common cause of JSONDecodeError in ADK).
    """
    from google.adk.models.lite_llm import LiteLlm  # noqa: PLC0415

    llm_kwargs = {"max_tokens": output_token_limit}

    if provider == "openrouter":
        api_key = _env("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set")
        litellm_id = model_id if model_id.startswith("openrouter/") else f"openrouter/{model_id}"
        return LiteLlm(
            model=litellm_id,
            api_base="https://openrouter.ai/api/v1",
            api_key=api_key,
            **llm_kwargs,
        )

    if provider == "openai-compatible":
        base_url = _env("OPENAI_BASE_URL", "http://localhost:11434/v1").rstrip("/")
        api_key = _env("OPENAI_API_KEY") or "local"
        litellm_id = model_id if model_id.startswith("openai/") else f"openai/{model_id}"
        return LiteLlm(
            model=litellm_id,
            api_base=base_url,
            api_key=api_key,
            **llm_kwargs,
        )

    # anthropic (default)
    if not _env("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    return LiteLlm(model=model_id, **llm_kwargs)


# --- ADK Event Formatter ------------------------------------------------------

def _format_event(event: Any) -> list[str]:
    """Convert a single ADK Event into zero or more log lines.

    ADK emits Event objects as the agent works.  Each event has:
      event.author  - "user", the agent name, or a tool name
      event.content - Content with a list of Part objects

    A Part can contain:
      part.text              -> plain text  ([assistant] prefix)
      part.function_call     -> tool the model wants to call  ([tool_use] prefix)
      part.function_response -> result sent back to model  ([result] prefix)
    """
    lines: list[str] = []
    try:
        content = getattr(event, "content", None)
        if content is None:
            return lines
        author = getattr(event, "author", "model")
        parts = getattr(content, "parts", None) or []

        for part in parts:
            text = getattr(part, "text", None)
            if text and text.strip():
                prefix = "[assistant]" if author != "user" else "[user]"
                for line in text.strip().split("\n"):
                    if line.strip():
                        lines.append(f"{prefix} {line}")

            fc = getattr(part, "function_call", None)
            if fc:
                name = getattr(fc, "name", "?")
                raw_args = getattr(fc, "args", {}) or {}
                args_str = ", ".join(
                    f"{k}={repr(str(v))[:80]}" for k, v in dict(raw_args).items()
                )
                lines.append(f"[tool_use] {name}({args_str})")

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


# --- Public Interface ---------------------------------------------------------

async def run_agent(
    agent_dir: Path,
    input_dir: Path,
    output_dir: Path,
    log_callback: Callable[[str], None] | None = None,
    stats_out: dict | None = None,
) -> None:
    """Run the ADK agent once.

    Emits log lines via log_callback (used by the web app for SSE streaming)
    and populates stats_out with total_turns / total_input_tokens /
    total_output_tokens.  Raises FileNotFoundError (missing instruction.md),
    RuntimeError (guardrail block, missing key), or provider errors.
    """
    from google.adk.agents import LlmAgent          # noqa: PLC0415
    from google.adk.runners import InMemoryRunner   # noqa: PLC0415
    from google.genai import types as genai_types   # noqa: PLC0415

    agent_dir = Path(agent_dir)
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    def emit(message: str) -> None:
        log.info(message)
        if log_callback:
            log_callback(message)

    provider = _env("API_PROVIDER", "anthropic").lower()
    model_id = _env("MODEL", DEFAULT_MODEL)
    max_turns = _env_int("MAX_TURNS", 50)
    output_token_limit = max_output_tokens()

    instruction, skills_block = load_agent_folder(agent_dir)

    input_files = _list_files(input_dir)
    is_safe, reason = await run_guardrail_check(instruction, input_files)
    emit(f"[guardrail] {reason}")
    if not is_safe:
        raise RuntimeError(f"Guardrail blocked the run: {reason}")

    skill_fns, skill_names = load_skills(agent_dir)
    custom_names = CUSTOM_TOOL_NAMES + skill_names
    system_prompt = build_system_prompt(instruction, skills_block, custom_names)

    emit(
        f"provider={provider}  model={model_id}  max_turns={max_turns}  "
        f"max_output_tokens={output_token_limit}  "
        f"shell={'enabled' if allow_shell() else 'DISABLED'}"
    )
    emit(f"agent={agent_dir}  input={input_dir}  output={output_dir}")

    model = _build_model(provider, model_id, output_token_limit=output_token_limit)
    tools = _make_tools(input_dir, output_dir) + CUSTOM_TOOLS + skill_fns

    agent = LlmAgent(
        name="file_processor",
        model=model,
        instruction=system_prompt,
        tools=tools,
        generate_content_config=genai_types.GenerateContentConfig(
            max_output_tokens=output_token_limit,
        ),
    )

    runner = InMemoryRunner(agent=agent, app_name="adk_agent")
    session = await runner.session_service.create_session(
        app_name="adk_agent",
        user_id="run_user",
    )

    user_message = genai_types.Content(
        role="user",
        parts=[genai_types.Part.from_text(text=KICKOFF_PROMPT)],
    )

    turns = 0
    tokens_in = 0
    tokens_out = 0

    try:
        async for event in runner.run_async(
            user_id="run_user",
            session_id=session.id,
            new_message=user_message,
        ):
            # Count model turns: each agent event that issues tool calls = 1 turn
            content = getattr(event, "content", None)
            author = getattr(event, "author", "")
            if author and author != "user" and content:
                parts = getattr(content, "parts", None) or []
                if any(getattr(p, "function_call", None) for p in parts):
                    turns += 1

            # Accumulate token usage from usage_metadata on model response events
            usage = getattr(event, "usage_metadata", None)
            if usage is not None:
                tokens_in += getattr(usage, "prompt_token_count", 0) or 0
                tokens_out += getattr(usage, "candidates_token_count", 0) or 0

            for line in _format_event(event):
                emit(line)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "The model returned malformed tool-call JSON (usually a truncated "
            "write_output with large content). Increase MAX_OUTPUT_TOKENS "
            f"(currently {output_token_limit}), use append_output for large "
            f"files, or switch to a model with a higher output limit. ({exc})"
        ) from exc

    emit(
        f"[result] turns={turns}  "
        f"tokens={tokens_in if tokens_in else '?'} in / "
        f"{tokens_out if tokens_out else '?'} out"
    )

    if stats_out is not None:
        stats_out["total_turns"] = turns or None
        stats_out["total_cost_usd"] = None
        stats_out["total_input_tokens"] = tokens_in or None
        stats_out["total_output_tokens"] = tokens_out or None


# --- Standalone Entry Point ---------------------------------------------------

def main() -> int:
    agent_dir = Path(_env("AGENT_DIR", "/app/agent"))
    input_dir = Path(_env("INPUT_DIR", "/app/input"))
    output_dir = Path(_env("OUTPUT_DIR", "/app/output"))
    output_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(output_dir / "agent.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    provider = _env("API_PROVIDER", "anthropic")
    model = _env("MODEL", DEFAULT_MODEL)
    max_turns = _env_int("MAX_TURNS", 50)

    # ASCII-only banner: Windows consoles often default to cp1252.
    print()
    print("  ADK Agent Harness - headless run")
    print("  ----------------------------------")
    print(f"  Started   : {datetime.now(timezone.utc).isoformat()}")
    print(f"  Provider  : {provider}")
    print(f"  Model     : {model}")
    print(f"  Max turns : {max_turns}")
    print(f"  Agent     : {agent_dir}")
    print(f"  Input     : {input_dir}")
    print(f"  Output    : {output_dir}")
    print("  ----------------------------------")
    print()

    try:
        asyncio.run(run_agent(agent_dir, input_dir, output_dir))
    except FileNotFoundError as exc:
        log.error("FATAL: %s", exc)
        return 1
    except RuntimeError as exc:
        log.error("FATAL: %s", exc)
        return 1
    except Exception as exc:
        log.exception("FATAL: unexpected error: %s", exc)
        return 1

    log.info("Agent run completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
