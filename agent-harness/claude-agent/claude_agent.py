#!/usr/bin/env python3
"""
Claude Agent Harness — core agent logic.

Reads agent/instruction.md (plus any skill .md files in agent/), processes
the job payload files in input/, and writes results to output/ using the
Anthropic Claude SDK (claude-agent-sdk).

Two entry points share this module:

    python claude_agent.py     headless run (CI/CD, containers)
    python web_app.py          Flask web UI (imports run_agent below)

Architecture
------------
  web_app.py / __main__  ->  run_agent()
                                |  dispatch on API_PROVIDER
                ┌───────────────┼────────────────────────┐
                ▼               ▼                        ▼
   _run_agent_anthropic   _run_agent_openrouter   _run_agent_openai_compat
   (claude-agent-sdk)     (anthropic SDK,         (httpx, OpenAI
                           custom base_url)        chat-completions format)
                |               |                        |
                └───────── tool dispatch ────────────────┘
                     list_input_files / read_input_file /
                     write_output / append_output /
                     list_output_files / run_command / web_fetch

Workshop exercises that touch this file:
  Exercise 3 -- Custom Tools : CUSTOM_TOOLS / CUSTOM_TOOL_NAMES
  Exercise 4 -- Guardrail    : run_guardrail_check()
  Exercise 5 -- Skill Loader : load_skills()
"""

import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import anyio
import httpx

log = logging.getLogger("claude_agent")

PROVIDERS = ("anthropic", "openrouter", "openai-compatible")

DEFAULT_MODEL = "claude-opus-4-5"
DEFAULT_MAX_OUTPUT_TOKENS = 16384
WEB_FETCH_MAX_BYTES = 512_000
WEB_FETCH_DEFAULT_TIMEOUT = 30


# --- Environment Helpers -------------------------------------------------------

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


def max_output_tokens() -> int:
    return _env_int("MAX_OUTPUT_TOKENS", DEFAULT_MAX_OUTPUT_TOKENS)


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


# --- Tool Specifications ------------------------------------------------------
#
# One canonical list of tool specs (JSON Schema) shared by all provider paths:
#   - Anthropic path  — converted to @tool-decorated SDK MCP tools
#   - OpenRouter path — passed as Anthropic-format `tools` parameter
#   - OpenAI-compat   — converted to OpenAI function-calling format

TOOL_SPECS: list[dict] = [
    {
        "name": "list_input_files",
        "description": "List payload files in the input folder. Returns a JSON array of relative file paths.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "read_input_file",
        "description": "Read a file from the input folder and return its text content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to the input folder"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_output",
        "description": (
            "Write (or overwrite) a file in the output folder. Creates parent directories as needed. "
            "Keep each call under ~8 KB; use append_output for larger files."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Destination path relative to the output folder"},
                "content": {"type": "string", "description": "Full text content to write"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "append_output",
        "description": "Append text to a file in the output folder (creates the file if absent).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Destination path relative to the output folder"},
                "content": {"type": "string", "description": "Text content to append"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_output_files",
        "description": "List files already written to the output folder (excluding agent.log). Returns a JSON array.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "run_command",
        "description": (
            "Execute a shell command and return its stdout, stderr and returncode as JSON. "
            "The working directory is the output folder."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute (piping and && are supported)"},
                "timeout": {"type": "integer", "description": "Max seconds the command may run (default 60)"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "web_fetch",
        "description": (
            "Fetch a URL over HTTP/HTTPS and return the response body as text. "
            "Use this to retrieve web pages or JSON API responses. "
            "Redirects are followed automatically."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Absolute http:// or https:// URL to fetch"},
                "timeout": {"type": "integer", "description": "Request timeout in seconds (default 30, max 60)"},
            },
            "required": ["url"],
        },
    },
]


# --- Tool Implementations -----------------------------------------------------

def _validate_fetch_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL must use http:// or https://")
    if not parsed.netloc:
        raise ValueError("URL must include a host")
    return url.strip()


def make_tool_impls(input_dir: Path, output_dir: Path) -> dict[str, Callable]:
    """Return {tool_name: async callable(args) -> str} bound to the run's folders.

    All provider paths dispatch tool calls through these implementations, so
    behaviour (and the path-traversal checks) is identical everywhere.
    """
    input_r = input_dir.resolve()
    output_r = output_dir.resolve()

    async def list_input_files(args: dict) -> str:
        return json.dumps(_list_files(input_r))

    async def read_input_file(args: dict) -> str:
        try:
            target = _safe_resolve(input_r, args["path"])
        except ValueError as exc:
            return f"Error: {exc}"
        if not target.is_file():
            return f"File not found: {args['path']}"
        return target.read_text(encoding="utf-8", errors="replace")

    async def write_output(args: dict) -> str:
        try:
            target = _safe_resolve(output_r, args["path"])
        except ValueError as exc:
            return f"Error: {exc}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(args["content"], encoding="utf-8")
        return f"Wrote {target.stat().st_size} bytes to {args['path']}"

    async def append_output(args: dict) -> str:
        try:
            target = _safe_resolve(output_r, args["path"])
        except ValueError as exc:
            return f"Error: {exc}"
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as fh:
            fh.write(args["content"])
        return f"Appended {len(args['content'])} chars to {args['path']}"

    async def list_output_files(args: dict) -> str:
        return json.dumps(_list_files(output_r, exclude={"agent.log"}))

    async def run_command(args: dict) -> str:
        return await _tool_run_command(args, cwd=output_r)

    async def web_fetch(args: dict) -> str:
        url = args.get("url", "")
        timeout = int(args.get("timeout") or WEB_FETCH_DEFAULT_TIMEOUT)
        try:
            fetch_url = _validate_fetch_url(url)
        except ValueError as exc:
            return json.dumps({"error": str(exc)})
        effective_timeout = min(max(int(timeout), 1), 60)
        try:
            with httpx.Client(
                follow_redirects=True,
                timeout=effective_timeout,
                headers={"User-Agent": "claude-agent-harness/1.0"},
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

    return {
        "list_input_files": list_input_files,
        "read_input_file": read_input_file,
        "write_output": write_output,
        "append_output": append_output,
        "list_output_files": list_output_files,
        "run_command": run_command,
        "web_fetch": web_fetch,
    }


async def _tool_run_command(args: dict, cwd: Path) -> str:
    """Execute a shell command with a timeout; capture stdout/stderr/returncode."""
    command = args["command"]
    timeout = int(args.get("timeout") or shell_timeout())

    if not allow_shell():
        log.warning("[tool] run_command blocked: ALLOW_SHELL=false")
        return "Shell access is disabled (ALLOW_SHELL=false)"

    try:
        with anyio.fail_after(timeout):
            proc = await anyio.run_process(
                command,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(cwd),
            )
    except TimeoutError:
        log.info("[tool] run_command(%s) -> timed out after %ds", command, timeout)
        return json.dumps({"stdout": "", "stderr": "Command timed out", "returncode": -1})

    result = {
        "stdout": proc.stdout.decode("utf-8", errors="replace"),
        "stderr": proc.stderr.decode("utf-8", errors="replace"),
        "returncode": proc.returncode,
    }
    log.info("[tool] run_command(%s) -> rc=%d", command, proc.returncode)
    return json.dumps(result)


async def _dispatch_tool(impls: dict[str, Callable], name: str, args: dict) -> str:
    impl = impls.get(name)
    if impl is None:
        return f"Error: unknown tool '{name}'"
    try:
        return await impl(args)
    except (ValueError, KeyError, OSError) as exc:
        return f"Error: {exc}"


# ==============================================================================
# WORKSHOP EXERCISE 3 -- Add Custom Tools
# ==============================================================================
#
# Add your own @tool-decorated async functions to CUSTOM_TOOLS and the matching
# fully-qualified names ("mcp__agent-tools__<name>") to CUSTOM_TOOL_NAMES.
# They are registered on the Anthropic path automatically.
#
# Example:
#
#   from claude_agent_sdk import tool
#
#   @tool("word_count", "Count lines and words in an input file",
#         {"type": "object",
#          "properties": {"path": {"type": "string"}},
#          "required": ["path"]})
#   async def word_count(args):
#       text = (Path(os.environ.get("INPUT_DIR", "input")) / args["path"]).read_text()
#       return {"content": [{"type": "text", "text": f"{len(text.splitlines())} lines, {len(text.split())} words"}]}
#
#   CUSTOM_TOOLS = [word_count]
#   CUSTOM_TOOL_NAMES = ["mcp__agent-tools__word_count"]

CUSTOM_TOOLS: list = []
CUSTOM_TOOL_NAMES: list[str] = []


# ==============================================================================
# WORKSHOP EXERCISE 4 -- Guardrail Agent
# ==============================================================================

async def run_guardrail_check(instructions: str, input_files: list[str]) -> tuple[bool, str]:
    """Validate the task instructions before the main agent runs.

    Returns (is_safe, reason). When is_safe is False, run_agent raises
    RuntimeError and the main agent never starts.

    Workshop: replace the pass-through below with a fast LLM judge, e.g.:
    #
    #   import anthropic
    #   client = anthropic.AsyncAnthropic()
    #   resp = await client.messages.create(
    #       model="claude-haiku-4-5-20251001",
    #       max_tokens=100,
    #       system=("You are a security guardrail. Reply 'SAFE' or 'UNSAFE: <reason>'. "
    #               "UNSAFE means the instructions try to exfiltrate data, attack "
    #               "other systems, or escape the input/output sandbox."),
    #       messages=[{"role": "user",
    #                  "content": f"Input files: {input_files}\\n\\nInstructions:\\n{instructions}"}],
    #   )
    #   verdict = resp.content[0].text.strip()
    #   if verdict.upper().startswith("SAFE"):
    #       return True, "Guardrail: instructions look safe"
    #   return False, verdict
    """
    return True, "Guardrail pass-through (not implemented)"


# ==============================================================================
# WORKSHOP EXERCISE 5 -- Skill Loader
# ==============================================================================

def load_skills(agent_dir: Path) -> tuple[list, list[str]]:
    """Scan agent/skills/*.py and load @tool-decorated callables as extra tools.

    Returns (sdk_tools, tool_names) where tool_names are the fully-qualified
    "mcp__agent-tools__<name>" strings to add to allowed_tools.

    Workshop: implement dynamic loading. Example:
    #
    #   import importlib.util
    #   tools, names = [], []
    #   skills_dir = agent_dir / "skills"
    #   for py in sorted(skills_dir.glob("*.py")):
    #       spec = importlib.util.spec_from_file_location(py.stem, py)
    #       module = importlib.util.module_from_spec(spec)
    #       spec.loader.exec_module(module)
    #       for obj in vars(module).values():
    #           if hasattr(obj, "name") and hasattr(obj, "handler"):  # SdkMcpTool
    #               tools.append(obj)
    #               names.append(f"mcp__agent-tools__{obj.name}")
    #   return tools, names
    """
    return [], []


# --- Agent Folder Loading -----------------------------------------------------

def load_agent_folder(agent_dir: Path) -> tuple[str, str]:
    """Return (instruction_text, skills_block) from the agent/ folder.

    instruction.md is required; every other top-level .md file is appended to
    the system prompt as a skill reference document.
    """
    instruction_file = agent_dir / "instruction.md"
    if not instruction_file.is_file():
        raise FileNotFoundError(f"instruction.md not found in {agent_dir}")
    instruction = instruction_file.read_text(encoding="utf-8")

    sections = []
    for md in sorted(agent_dir.glob("*.md")):
        if md.name == "instruction.md":
            continue
        sections.append(f"### {md.name}\n\n{md.read_text(encoding='utf-8')}")
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
        f"  - {name.removeprefix('mcp__agent-tools__')}  (custom skill)\n"
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
        "  - For larger files, use append_output in several smaller chunks.\n"
        "\n"
        f"{shell_block}"
    )

    if skills_block:
        prompt += f"\n## Skills\n\n{skills_block}\n"

    prompt += f"\nTASK INSTRUCTIONS:\n{instruction}"
    return prompt


KICKOFF_PROMPT = "Begin executing the task instructions now."


# --- Public Interface ---------------------------------------------------------

async def run_agent(
    agent_dir: Path,
    input_dir: Path,
    output_dir: Path,
    log_callback: Callable[[str], None] | None = None,
    stats_out: dict | None = None,
    cancel_event=None,
) -> None:
    """Run the agent once. Dispatches to the provider path named by API_PROVIDER.

    Emits log lines via log_callback (used by the web app for SSE streaming)
    and populates stats_out with total_turns / total_cost_usd / token counts.
    Raises FileNotFoundError (missing instruction.md), RuntimeError (guardrail
    block or unknown provider), or provider/SDK errors.

    cancel_event: optional threading.Event; when set, the agent stops after
    the current tool call completes.
    """
    agent_dir = Path(agent_dir)
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    def emit(message: str) -> None:
        log.info(message)
        if log_callback:
            log_callback(message)

    provider = _env("API_PROVIDER", "anthropic").lower()
    model = _env("MODEL", DEFAULT_MODEL)
    max_turns = _env_int("MAX_TURNS", 50)

    instruction, skills_block = load_agent_folder(agent_dir)

    input_files = _list_files(input_dir)
    is_safe, reason = await run_guardrail_check(instruction, input_files)
    emit(f"[guardrail] {reason}")
    if not is_safe:
        raise RuntimeError(f"Guardrail blocked the run: {reason}")

    skill_tools, skill_names = load_skills(agent_dir)
    custom_names = CUSTOM_TOOL_NAMES + skill_names
    system_prompt = build_system_prompt(instruction, skills_block, custom_names)

    emit(
        f"provider={provider}  model={model}  max_turns={max_turns}  "
        f"shell={'enabled' if allow_shell() else 'DISABLED'}"
    )
    emit(f"agent={agent_dir}  input={input_dir}  output={output_dir}")

    if provider == "anthropic":
        await _run_agent_anthropic(
            system_prompt, input_dir, output_dir, model, max_turns,
            skill_tools, custom_names, emit, stats_out, cancel_event,
        )
    elif provider == "openrouter":
        await _run_agent_openrouter(
            system_prompt, input_dir, output_dir, model, max_turns, emit, stats_out, cancel_event,
        )
    elif provider == "openai-compatible":
        await _run_agent_openai_compat(
            system_prompt, input_dir, output_dir, model, max_turns, emit, stats_out, cancel_event,
        )
    else:
        raise RuntimeError(f"Unknown API_PROVIDER: {provider!r} (expected one of {PROVIDERS})")


# --- Provider Path: Anthropic (claude-agent-sdk) ------------------------------

def make_tools(input_dir: Path, output_dir: Path) -> list:
    """Wrap the shared tool implementations as claude-agent-sdk @tool objects."""
    from claude_agent_sdk import tool  # noqa: PLC0415

    impls = make_tool_impls(input_dir, output_dir)
    sdk_tools = []
    for spec in TOOL_SPECS:
        impl = impls[spec["name"]]

        @tool(spec["name"], spec["description"], spec["input_schema"])
        async def handler(args: dict, _impl=impl) -> dict:
            try:
                text = await _impl(args)
            except (ValueError, OSError) as exc:
                text = f"Error: {exc}"
            return {"content": [{"type": "text", "text": text}]}

        sdk_tools.append(handler)
    return sdk_tools


async def _run_agent_anthropic(
    system_prompt: str,
    input_dir: Path,
    output_dir: Path,
    model: str,
    max_turns: int,
    extra_tools: list,
    extra_tool_names: list[str],
    emit: Callable[[str], None],
    stats_out: dict | None,
    cancel_event=None,
) -> None:
    from claude_agent_sdk import (  # noqa: PLC0415
        AssistantMessage,
        ClaudeAgentOptions,
        ClaudeSDKClient,
        ResultMessage,
        TextBlock,
        ToolResultBlock,
        ToolUseBlock,
        UserMessage,
        create_sdk_mcp_server,
    )

    if not _env("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    tools = make_tools(input_dir, output_dir) + CUSTOM_TOOLS + extra_tools
    server = create_sdk_mcp_server(name="agent-tools", version="1.0.0", tools=tools)

    allowed_tools = [f"mcp__agent-tools__{spec['name']}" for spec in TOOL_SPECS]
    allowed_tools += extra_tool_names

    disallowed_tools = ["Read", "Write", "Edit", "MultiEdit", "WebSearch"]
    if not allow_shell():
        disallowed_tools.append("Bash")

    options = ClaudeAgentOptions(
        model=model,
        max_turns=max_turns,
        system_prompt=system_prompt,
        mcp_servers={"agent-tools": server},
        allowed_tools=allowed_tools,
        disallowed_tools=disallowed_tools,
        permission_mode="acceptEdits",
        cwd=str(output_dir),
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(KICKOFF_PROMPT)
        async for msg in client.receive_response():
            if cancel_event and cancel_event.is_set():
                emit("[agent] Run cancelled by user")
                break
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        for line in block.text.strip().splitlines():
                            if line.strip():
                                emit(f"[assistant] {line}")
                    elif isinstance(block, ToolUseBlock):
                        args_str = ", ".join(
                            f"{k}={repr(str(v))[:80]}" for k, v in (block.input or {}).items()
                        )
                        emit(f"[tool_use] {block.name}({args_str})")
            elif isinstance(msg, UserMessage):
                content = msg.content if isinstance(msg.content, list) else []
                for block in content:
                    if isinstance(block, ToolResultBlock):
                        emit(f"[result] {_summarise_tool_result(block.content)}")
            elif isinstance(msg, ResultMessage):
                cost = msg.total_cost_usd
                tokens_in, tokens_out = _extract_usage(getattr(msg, "usage", None))
                emit(
                    f"[result] turns={msg.num_turns}  "
                    f"cost={'$%.4f' % cost if cost is not None else 'n/a'}  "
                    f"tokens={tokens_in if tokens_in is not None else '?'} in / "
                    f"{tokens_out if tokens_out is not None else '?'} out  "
                    f"stop={msg.subtype}"
                )
                if stats_out is not None:
                    stats_out["total_turns"] = msg.num_turns
                    stats_out["total_cost_usd"] = msg.total_cost_usd
                    stats_out["total_input_tokens"] = tokens_in
                    stats_out["total_output_tokens"] = tokens_out


def _extract_usage(usage: Any) -> tuple[int | None, int | None]:
    """Return (input_tokens, output_tokens) from an SDK/API usage payload."""
    if usage is None:
        return None, None
    get = usage.get if isinstance(usage, dict) else lambda k, d=None: getattr(usage, k, d)
    tokens_in = (
        (get("input_tokens") or 0)
        + (get("cache_creation_input_tokens") or 0)
        + (get("cache_read_input_tokens") or 0)
    )
    tokens_out = get("output_tokens")
    if tokens_in == 0 and tokens_out is None:
        return None, None
    return tokens_in, tokens_out or 0


def _summarise_tool_result(content: Any, limit: int = 300) -> str:
    """Flatten an SDK/API tool-result content payload into a short log string."""
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text", item)))
            else:
                parts.append(str(getattr(item, "text", item)))
        text = " ".join(parts)
    else:
        text = str(content)
    text = " ".join(text.split())
    return text[:limit] + ("..." if len(text) > limit else "")


# --- Provider Path: OpenRouter (anthropic SDK, custom base_url) ---------------

def _anthropic_format_tools() -> list[dict]:
    return [
        {"name": s["name"], "description": s["description"], "input_schema": s["input_schema"]}
        for s in TOOL_SPECS
    ]


async def _run_agent_openrouter(
    system_prompt: str,
    input_dir: Path,
    output_dir: Path,
    model: str,
    max_turns: int,
    emit: Callable[[str], None],
    stats_out: dict | None,
    cancel_event=None,
) -> None:
    import anthropic  # noqa: PLC0415

    api_key = _env("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    client = anthropic.AsyncAnthropic(
        api_key=api_key,
        base_url="https://openrouter.ai/api",
        default_headers={
            "HTTP-Referer": "https://github.com/agent-harness",
            "X-Title": "Claude Agent Harness",
        },
    )

    impls = make_tool_impls(input_dir, output_dir)
    tools = _anthropic_format_tools()
    messages: list[dict] = [{"role": "user", "content": KICKOFF_PROMPT}]
    turns = 0
    tokens_in = 0
    tokens_out = 0
    output_token_limit = max_output_tokens()

    for turn in range(1, max_turns + 1):
        if cancel_event and cancel_event.is_set():
            emit("[agent] Run cancelled by user")
            break
        turns = turn
        response = await client.messages.create(
            model=model,
            max_tokens=output_token_limit,
            system=system_prompt,
            messages=messages,
            tools=tools,
        )
        t_in, t_out = _extract_usage(getattr(response, "usage", None))
        tokens_in += t_in or 0
        tokens_out += t_out or 0
        emit(f"[turn {turn}/{max_turns}] stop_reason={response.stop_reason}")

        tool_results = []
        for block in response.content:
            if block.type == "text" and block.text.strip():
                for line in block.text.strip().splitlines():
                    if line.strip():
                        emit(f"[assistant] {line}")
            elif block.type == "tool_use":
                args_str = ", ".join(f"{k}={repr(str(v))[:80]}" for k, v in (block.input or {}).items())
                emit(f"[tool_use] {block.name}({args_str})")
                result_text = await _dispatch_tool(impls, block.name, dict(block.input or {}))
                emit(f"[result] {_summarise_tool_result(result_text)}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                })

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn" or not tool_results:
            break
        messages.append({"role": "user", "content": tool_results})
    else:
        emit(f"[WARNING] max_turns ({max_turns}) reached before the agent finished")

    emit(f"[result] turns={turns}  tokens={tokens_in} in / {tokens_out} out")
    if stats_out is not None:
        stats_out["total_turns"] = turns
        stats_out["total_cost_usd"] = None
        stats_out["total_input_tokens"] = tokens_in
        stats_out["total_output_tokens"] = tokens_out


# --- Provider Path: OpenAI-compatible (local servers, httpx) ------------------

def _openai_format_tools() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": s["name"],
                "description": s["description"],
                "parameters": s["input_schema"],
            },
        }
        for s in TOOL_SPECS
    ]


async def _run_agent_openai_compat(
    system_prompt: str,
    input_dir: Path,
    output_dir: Path,
    model: str,
    max_turns: int,
    emit: Callable[[str], None],
    stats_out: dict | None,
    cancel_event=None,
) -> None:
    base_url = _env("OPENAI_BASE_URL", "http://localhost:11434/v1").rstrip("/")
    api_key = _env("OPENAI_API_KEY")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    impls = make_tool_impls(input_dir, output_dir)
    tools = _openai_format_tools()
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": KICKOFF_PROMPT},
    ]
    turns = 0
    tokens_in = 0
    tokens_out = 0
    output_token_limit = max_output_tokens()

    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=15.0)) as client:
        for turn in range(1, max_turns + 1):
            if cancel_event and cancel_event.is_set():
                emit("[agent] Run cancelled by user")
                break
            turns = turn
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json={"model": model, "messages": messages, "tools": tools, "max_tokens": output_token_limit},
            )
            resp.raise_for_status()
            body = resp.json()
            usage = body.get("usage") or {}
            tokens_in += usage.get("prompt_tokens") or 0
            tokens_out += usage.get("completion_tokens") or 0
            choice = body["choices"][0]
            message = choice["message"]
            finish = choice.get("finish_reason")
            emit(f"[turn {turn}/{max_turns}] finish_reason={finish}")

            if message.get("content"):
                for line in str(message["content"]).strip().splitlines():
                    if line.strip():
                        emit(f"[assistant] {line}")

            messages.append(message)

            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                break

            for tc in tool_calls:
                name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                args_str = ", ".join(f"{k}={repr(str(v))[:80]}" for k, v in args.items())
                emit(f"[tool_use] {name}({args_str})")
                result_text = await _dispatch_tool(impls, name, args)
                emit(f"[result] {_summarise_tool_result(result_text)}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", name),
                    "content": result_text,
                })
        else:
            emit(f"[WARNING] max_turns ({max_turns}) reached before the agent finished")

    emit(f"[result] turns={turns}  tokens={tokens_in} in / {tokens_out} out")
    if stats_out is not None:
        stats_out["total_turns"] = turns
        stats_out["total_cost_usd"] = None
        stats_out["total_input_tokens"] = tokens_in
        stats_out["total_output_tokens"] = tokens_out


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

    print()
    print("  Claude Agent Harness - headless run")
    print("  -------------------------------------")
    print(f"  Started   : {datetime.now(timezone.utc).isoformat()}")
    print(f"  Provider  : {provider}")
    print(f"  Model     : {model}")
    print(f"  Max turns : {max_turns}")
    print(f"  Agent     : {agent_dir}")
    print(f"  Input     : {input_dir}")
    print(f"  Output    : {output_dir}")
    print("  -------------------------------------")
    print()

    try:
        anyio.run(run_agent, agent_dir, input_dir, output_dir)
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
