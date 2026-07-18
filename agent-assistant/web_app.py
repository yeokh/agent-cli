#!/usr/bin/env python3
"""
Interactive Pydantic Assistant - Flask Web Server

Provides a chat UI for multi-turn conversational AI powered by Pydantic AI.
"""

import asyncio
import json
import logging
import os
import queue
import re
import shutil
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import httpx
from flask import Flask, Response, jsonify, render_template, request, stream_with_context

import chat_agent

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

AGENT_DIR  = Path(os.environ.get("AGENT_DIR",  "./agent")).resolve()
INPUT_DIR  = Path(os.environ.get("INPUT_DIR",  "./input")).resolve()
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "./output")).resolve()
PORT = int(os.environ.get("PORT", "8081"))
HOST = os.environ.get("HOST", "0.0.0.0")

for _d in (AGENT_DIR, INPUT_DIR, OUTPUT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

INSTRUCTION_FILE = AGENT_DIR / "instruction.md"
HIDDEN_FILES = {".gitkeep"}

KEY_ENV_VARS = {
    "anthropic":         "ANTHROPIC_API_KEY",
    "openai":            "OPENAI_API_KEY",
    "openrouter":        "OPENROUTER_API_KEY",
    "openai-compatible": "OPENAI_API_KEY",
    "gemini":            "GEMINI_API_KEY",
    "groq":              "GROQ_API_KEY",
    "mistral":           "MISTRAL_API_KEY",
}
NO_KEY_PROVIDERS = {"openai-compatible"}

# ---------------------------------------------------------------------------
# Application log capture
# ---------------------------------------------------------------------------

class _DequeHandler(logging.Handler):
    def __init__(self, maxlen: int = 500):
        super().__init__()
        self._records: deque = deque(maxlen=maxlen)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._records.append({
                "time": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                "level": record.levelname,
                "msg": self.format(record),
            })
        except Exception:
            pass

    def snapshot(self, offset: int = 0) -> list:
        return list(self._records)[offset:]


_app_log_handler = _DequeHandler(maxlen=500)
_app_log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logging.getLogger().addHandler(_app_log_handler)

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(__name__)
log = logging.getLogger("web_app")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Chat session
# ---------------------------------------------------------------------------

class ChatSession:
    """Thread-safe conversation session."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.instruction: str = ""
        self.model_messages: list = []
        self.display_messages: list = []
        self.status: str = "idle"
        self.cancel_event = threading.Event()
        self._agent_thread = None

    def reset(self, instruction: str) -> None:
        with self._lock:
            self.status = "idle"
            self.instruction = instruction
            self.model_messages = []
            self.display_messages = []
            if instruction.strip():
                self.display_messages.append({
                    "id": str(uuid.uuid4()),
                    "role": "you",
                    "type": "instruction",
                    "content": instruction,
                    "timestamp": _now(),
                })

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "status": self.status,
                "display_messages": list(self.display_messages),
            }

    def add_display_message(self, msg: dict) -> None:
        with self._lock:
            self.display_messages.append(msg)

    def update_model_messages(self, messages: list) -> None:
        with self._lock:
            self.model_messages = messages

    def get_model_messages(self) -> list:
        with self._lock:
            return list(self.model_messages)

    def get_instruction(self) -> str:
        with self._lock:
            return self.instruction

    def set_status(self, status: str) -> None:
        with self._lock:
            self.status = status


session = ChatSession()


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def _read_instruction() -> str:
    if INSTRUCTION_FILE.is_file():
        return INSTRUCTION_FILE.read_text(encoding="utf-8", errors="replace")
    return ""


def _write_instruction(content: str) -> None:
    INSTRUCTION_FILE.parent.mkdir(parents=True, exist_ok=True)
    INSTRUCTION_FILE.write_text(content, encoding="utf-8")


def _load_skills() -> tuple:
    """Return (combined_text, list_of_filenames) for all skill .md files."""
    sections = []
    files = []
    for md in sorted(AGENT_DIR.glob("*.md")):
        if md.name == "instruction.md":
            continue
        body = md.read_text(encoding="utf-8", errors="replace")
        sections.append(f"### {md.name}\n\n{body}")
        files.append(md.name)
    return "\n\n---\n\n".join(sections), files


def _safe_path(base: Path, rel: str) -> Path:
    target = (base / rel).resolve()
    if not str(target).startswith(str(base.resolve())):
        raise ValueError(f"Path traversal denied: {rel}")
    return target


def _list_dir(directory: Path) -> list:
    result = []
    if not directory.exists():
        return result
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.name in HIDDEN_FILES:
            continue
        stat = path.stat()
        result.append({
            "name": str(path.relative_to(directory)).replace("\\", "/"),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        })
    return result


def _sanitise_filename(raw: str) -> str:
    return re.sub(r"[^\w.\-/]", "_", raw)


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# ---------------------------------------------------------------------------
# Agent thread
# ---------------------------------------------------------------------------

def _run_agent_thread(
    user_message: str,
    prev_model_messages: list,
    instruction: str,
    event_queue: queue.Queue,
) -> None:
    session.set_status("running")
    session.cancel_event.clear()

    ai_text_parts = []
    tool_events = []

    def on_event(ev: dict) -> None:
        if ev["type"] == "delta":
            ai_text_parts.append(ev["content"])
        elif ev["type"] in ("tool_use", "tool_result"):
            tool_events.append(ev)
        event_queue.put(ev)

    try:
        new_messages = asyncio.run(
            chat_agent.run_chat_turn(
                user_message=user_message,
                model_messages=prev_model_messages,
                agent_dir=AGENT_DIR,
                input_dir=INPUT_DIR,
                output_dir=OUTPUT_DIR,
                instruction=instruction,
                event_callback=on_event,
                cancel_event=session.cancel_event,
            )
        )
        session.update_model_messages(new_messages)

        full_text = "".join(ai_text_parts)
        ai_msg = {
            "id": str(uuid.uuid4()),
            "role": "ai",
            "type": "text",
            "content": full_text,
            "tool_events": tool_events,
            "timestamp": _now(),
        }
        session.add_display_message(ai_msg)
        event_queue.put({"type": "done", "message": ai_msg})

    except Exception as exc:
        log.exception("Agent turn failed: %s", exc)
        err_msg = {
            "id": str(uuid.uuid4()),
            "role": "ai",
            "type": "error",
            "content": str(exc),
            "tool_events": [],
            "timestamp": _now(),
        }
        session.add_display_message(err_msg)
        event_queue.put({"type": "error", "content": str(exc), "message": err_msg})
    finally:
        session.set_status("idle")


# ---------------------------------------------------------------------------
# Routes: Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Routes: Session
# ---------------------------------------------------------------------------

@app.route("/api/session", methods=["GET"])
def api_session():
    return jsonify(session.snapshot())


@app.route("/api/chat/reset", methods=["POST"])
def api_chat_reset():
    if session.status == "running":
        return jsonify({"error": "Cannot reset while a turn is running"}), 409
    instruction = _read_instruction()
    session.reset(instruction)
    log.info("Session reset")
    return jsonify(session.snapshot())


@app.route("/api/chat/cancel", methods=["POST"])
def api_chat_cancel():
    if session.status != "running":
        return jsonify({"error": "No turn in progress"}), 409
    session.cancel_event.set()
    return jsonify({"status": "cancelling"})


# ---------------------------------------------------------------------------
# Routes: Chat (SSE)
# ---------------------------------------------------------------------------

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "Empty message"}), 400
    if session.status == "running":
        return jsonify({"error": "A turn is already in progress"}), 409

    # /skills command
    if message.lower() in ("/skills", "/skill"):
        def _skills_stream():
            skills_text, skill_files = _load_skills()
            if not skills_text:
                content = "No skill files found in the agent folder."
                skill_files = []
            else:
                content = skills_text

            display_msg = {
                "id": str(uuid.uuid4()),
                "role": "you",
                "type": "skills",
                "content": content,
                "files": skill_files,
                "timestamp": _now(),
            }
            session.add_display_message(display_msg)

            if skills_text:
                from pydantic_ai import ModelRequest, UserPromptPart
                skills_prompt = (
                    "The following skill reference documents are now available:\n\n"
                    + skills_text
                )
                new_msg = ModelRequest(parts=[UserPromptPart(content=skills_prompt)])
                prev = session.get_model_messages()
                session.update_model_messages(prev + [new_msg])

            yield _sse({"type": "done", "message": display_msg})

        return Response(
            stream_with_context(_skills_stream()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # Regular message
    user_msg = {
        "id": str(uuid.uuid4()),
        "role": "you",
        "type": "user",
        "content": message,
        "timestamp": _now(),
    }
    session.add_display_message(user_msg)

    prev_model_messages = session.get_model_messages()
    instruction = session.get_instruction()
    event_q: queue.Queue = queue.Queue()

    thread = threading.Thread(
        target=_run_agent_thread,
        args=(message, prev_model_messages, instruction, event_q),
        daemon=True,
        name="agent-turn",
    )
    session._agent_thread = thread
    thread.start()

    def _generate():
        yield _sse({"type": "user_message", "message": user_msg})
        while True:
            try:
                ev = event_q.get(timeout=60)
                yield _sse(ev)
                if ev.get("type") in ("done", "error"):
                    return
            except queue.Empty:
                if not thread.is_alive():
                    return
                yield _sse({"type": "ping"})

    return Response(
        stream_with_context(_generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Routes: Instruction
# ---------------------------------------------------------------------------

@app.route("/api/instruction", methods=["GET"])
def api_get_instruction():
    content = _read_instruction()
    return jsonify({"content": content, "exists": INSTRUCTION_FILE.is_file()})


@app.route("/api/instruction", methods=["PUT"])
def api_put_instruction():
    if session.status == "running":
        return jsonify({"error": "Cannot edit instructions while a turn is running"}), 409
    data = request.get_json(silent=True) or {}
    content = data.get("content", "")
    _write_instruction(content)
    session.reset(content)
    log.info("instruction.md saved and session reset (%d chars)", len(content))
    return jsonify({"saved": True, **session.snapshot()})


# ---------------------------------------------------------------------------
# Routes: Files
# ---------------------------------------------------------------------------

@app.route("/api/input", methods=["GET"])
def api_list_input():
    return jsonify({"files": _list_dir(INPUT_DIR)})


@app.route("/api/output", methods=["GET"])
def api_list_output():
    return jsonify({"files": _list_dir(OUTPUT_DIR)})


@app.route("/api/upload/input", methods=["POST"])
def api_upload_input():
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400
    safe_name = _sanitise_filename(file.filename)
    try:
        target = _safe_path(INPUT_DIR, safe_name)
        target.parent.mkdir(parents=True, exist_ok=True)
        file.save(target)
        log.info("Uploaded input/%s (%d bytes)", safe_name, target.stat().st_size)
        return jsonify({"name": safe_name, "size": target.stat().st_size})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/input/<path:filename>", methods=["DELETE"])
def api_delete_input(filename):
    try:
        target = _safe_path(INPUT_DIR, filename)
        if target.exists():
            target.unlink()
        return jsonify({"deleted": filename})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/output", methods=["DELETE"])
def api_clear_output():
    for item in OUTPUT_DIR.iterdir():
        if item.name in HIDDEN_FILES:
            continue
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
    log.info("Output folder cleared")
    return jsonify({"cleared": True})


@app.route("/api/agent", methods=["GET"])
def api_list_agent():
    return jsonify({"files": _list_dir(AGENT_DIR)})


@app.route("/api/input", methods=["DELETE"])
def api_clear_input():
    for item in INPUT_DIR.iterdir():
        if item.name in HIDDEN_FILES:
            continue
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
    log.info("Input folder cleared")
    return jsonify({"cleared": True})


@app.route("/api/file/<any('agent','input','output'):folder>/<path:filename>", methods=["GET", "PUT", "DELETE"])
def api_read_file(folder, filename):
    base = {"agent": AGENT_DIR, "input": INPUT_DIR, "output": OUTPUT_DIR}[folder]

    if request.method == "GET":
        try:
            target = _safe_path(base, filename)
            if not target.is_file():
                return jsonify({"error": f"File not found: {filename}"}), 404
            return jsonify({
                "name": filename,
                "content": target.read_text(encoding="utf-8", errors="replace"),
            })
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404

    if request.method == "PUT":
        if folder == "output":
            return jsonify({"error": "Output folder is read-only via this endpoint"}), 403
        data = request.get_json(silent=True) or {}
        content = data.get("content", "")
        safe_name = _sanitise_filename(filename) if folder == "input" else filename
        try:
            target = _safe_path(base, safe_name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            log.info("Written %s/%s (%d chars)", folder, safe_name, len(content))
            return jsonify({"name": safe_name, "size": target.stat().st_size})
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    if request.method == "DELETE":
        if folder == "output":
            return jsonify({"error": "Use DELETE /api/output to clear output files"}), 403
        try:
            target = _safe_path(base, filename)
            if target.exists():
                target.unlink()
            log.info("Deleted %s/%s", folder, filename)
            return jsonify({"deleted": filename})
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400


# ---------------------------------------------------------------------------
# Routes: App Logs (SSE)
# ---------------------------------------------------------------------------

@app.route("/api/app-logs", methods=["GET"])
def api_app_logs():
    offset = int(request.args.get("offset", 0))

    def _generate():
        sent = offset
        while True:
            for entry in _app_log_handler.snapshot(offset=sent):
                yield _sse(entry)
                sent += 1
            time.sleep(1.0)

    return Response(
        stream_with_context(_generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Routes: Provider & Model
# ---------------------------------------------------------------------------

_model_cache: dict = {}
_model_cache_lock = threading.Lock()
_MODEL_CACHE_TTL = 300.0


def _fetch_models(provider: str) -> list:
    with _model_cache_lock:
        cached = _model_cache.get(provider)
        if cached and time.monotonic() - cached[0] < _MODEL_CACHE_TTL:
            return cached[1]

    models = []
    try:
        if provider == "anthropic":
            key = os.environ.get("ANTHROPIC_API_KEY", "")
            if key:
                resp = httpx.get(
                    "https://api.anthropic.com/v1/models",
                    headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                    timeout=10,
                )
                resp.raise_for_status()
                models = [
                    {"id": m["id"], "name": m.get("display_name", m["id"])}
                    for m in resp.json().get("data", [])
                ]
        elif provider == "openai":
            key = os.environ.get("OPENAI_API_KEY", "")
            if key:
                resp = httpx.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {key}"},
                    timeout=10,
                )
                resp.raise_for_status()
                models = [
                    {"id": m["id"], "name": m["id"]}
                    for m in resp.json().get("data", [])
                    if any(m["id"].startswith(p) for p in ("gpt-", "o1", "o3", "o4"))
                ]
                models.sort(key=lambda m: m["id"])
        elif provider == "openrouter":
            key = os.environ.get("OPENROUTER_API_KEY", "")
            if key:
                resp = httpx.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {key}"},
                    timeout=15,
                )
                resp.raise_for_status()
                models = [
                    {"id": m["id"], "name": m.get("name", m["id"])}
                    for m in resp.json().get("data", [])
                    if "tools" in (m.get("supported_parameters") or [])
                ]
        elif provider == "openai-compatible":
            base = os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1").rstrip("/")
            headers = {}
            key = os.environ.get("OPENAI_API_KEY", "")
            if key:
                headers["Authorization"] = f"Bearer {key}"
            resp = httpx.get(f"{base}/models", headers=headers, timeout=10)
            resp.raise_for_status()
            models = [{"id": m["id"], "name": m["id"]} for m in resp.json().get("data", [])]
        elif provider == "gemini":
            key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
            if key:
                resp = httpx.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
                    timeout=10,
                )
                resp.raise_for_status()
                models = [
                    {
                        "id": m["name"].split("/")[-1],
                        "name": m.get("displayName", m["name"].split("/")[-1]),
                    }
                    for m in resp.json().get("models", [])
                    if "generateContent" in m.get("supportedGenerationMethods", [])
                ]
        elif provider == "groq":
            key = os.environ.get("GROQ_API_KEY", "")
            if key:
                resp = httpx.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {key}"},
                    timeout=10,
                )
                resp.raise_for_status()
                models = [{"id": m["id"], "name": m["id"]} for m in resp.json().get("data", [])]
                models.sort(key=lambda m: m["id"])
        elif provider == "mistral":
            key = os.environ.get("MISTRAL_API_KEY", "")
            if key:
                resp = httpx.get(
                    "https://api.mistral.ai/v1/models",
                    headers={"Authorization": f"Bearer {key}"},
                    timeout=10,
                )
                resp.raise_for_status()
                models = [
                    {"id": m["id"], "name": m.get("name", m["id"])}
                    for m in resp.json().get("data", [])
                ]
    except Exception as exc:
        log.warning("Failed to fetch %s models: %s", provider, exc)

    with _model_cache_lock:
        _model_cache[provider] = (time.monotonic(), models)
    return models


@app.route("/api/providers", methods=["GET"])
def api_providers():
    return jsonify({
        "providers": list(chat_agent.PROVIDERS),
        "current": os.environ.get("API_PROVIDER", "anthropic"),
    })


@app.route("/api/provider", methods=["GET"])
def api_get_provider():
    return jsonify({"provider": os.environ.get("API_PROVIDER", "anthropic")})


@app.route("/api/provider", methods=["POST"])
def api_set_provider():
    data = request.get_json(silent=True) or {}
    provider = data.get("provider", "")
    if provider not in chat_agent.PROVIDERS:
        return jsonify({"error": f"Unknown provider: {provider}"}), 400
    os.environ["API_PROVIDER"] = provider
    log.info("Provider set to: %s", provider)
    return jsonify({"provider": provider})


@app.route("/api/models", methods=["GET"])
def api_models():
    provider = request.args.get("provider") or os.environ.get("API_PROVIDER", "anthropic")
    if provider not in chat_agent.PROVIDERS:
        return jsonify({"error": f"Unknown provider: {provider}"}), 400
    return jsonify({"models": _fetch_models(provider), "provider": provider})


@app.route("/api/model", methods=["GET"])
def api_get_model():
    provider = os.environ.get("API_PROVIDER", "anthropic")
    default_model = chat_agent.DEFAULT_MODEL_BY_PROVIDER.get(provider, chat_agent.DEFAULT_MODEL)
    return jsonify({
        "model": os.environ.get("MODEL", default_model),
        "provider": provider,
    })


@app.route("/api/model", methods=["POST"])
def api_set_model():
    data = request.get_json(silent=True) or {}
    model = data.get("model", "").strip()
    if not model:
        return jsonify({"error": "Missing 'model'"}), 400
    os.environ["MODEL"] = model
    log.info("Model set to: %s", model)
    return jsonify({"model": model})


# ---------------------------------------------------------------------------
# Routes: API Keys
# ---------------------------------------------------------------------------

@app.route("/api/keys", methods=["GET"])
def api_get_keys():
    return jsonify({
        provider: bool(os.environ.get(env_var))
        for provider, env_var in KEY_ENV_VARS.items()
    })


@app.route("/api/keys", methods=["POST"])
def api_set_key():
    data = request.get_json(silent=True) or {}
    provider = data.get("provider", "")
    key = data.get("key", "")
    if provider not in KEY_ENV_VARS:
        return jsonify({"error": f"Unknown provider: {provider}"}), 400
    if not key:
        return jsonify({"error": "Missing 'key'"}), 400
    os.environ[KEY_ENV_VARS[provider]] = key
    if provider == "gemini":
        os.environ["GOOGLE_API_KEY"] = key
    with _model_cache_lock:
        _model_cache.pop(provider, None)
    log.info("API key set for provider: %s", provider)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Routes: Tools
# ---------------------------------------------------------------------------

@app.route("/api/tools", methods=["GET"])
def api_get_tools():
    disabled = chat_agent.disabled_tool_names()
    return jsonify({
        "tools": [
            {**t, "enabled": t["name"] not in disabled}
            for t in chat_agent.TOOL_CATALOG
        ]
    })


@app.route("/api/tools", methods=["POST"])
def api_set_tools():
    data = request.get_json(silent=True) or {}
    valid_names = {t["name"] for t in chat_agent.TOOL_CATALOG}
    disabled = {name for name, enabled in data.items() if name in valid_names and not enabled}
    os.environ["DISABLED_TOOLS"] = ",".join(sorted(disabled))
    log.info("Disabled tools updated: %s", disabled or "none")
    return api_get_tools()


# ---------------------------------------------------------------------------
# Routes: Settings
# ---------------------------------------------------------------------------

@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    return jsonify({
        "max_turns": int(os.environ.get("MAX_TURNS", "50") or 50),
        "max_output_tokens": int(
            os.environ.get("MAX_OUTPUT_TOKENS", str(chat_agent.DEFAULT_MAX_OUTPUT_TOKENS))
            or chat_agent.DEFAULT_MAX_OUTPUT_TOKENS
        ),
        "allow_shell": os.environ.get("ALLOW_SHELL", "true").lower() not in ("0", "false", "no", "off"),
        "shell_timeout": int(os.environ.get("SHELL_TIMEOUT", "60") or 60),
        "openai_base_url": os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1"),
    })


@app.route("/api/settings", methods=["POST"])
def api_set_settings():
    data = request.get_json(silent=True) or {}
    if "max_turns" in data:
        try:
            os.environ["MAX_TURNS"] = str(max(1, int(data["max_turns"])))
        except (TypeError, ValueError):
            return jsonify({"error": "max_turns must be an integer"}), 400
    if "max_output_tokens" in data:
        try:
            os.environ["MAX_OUTPUT_TOKENS"] = str(max(1024, int(data["max_output_tokens"])))
        except (TypeError, ValueError):
            return jsonify({"error": "max_output_tokens must be an integer"}), 400
    if "allow_shell" in data:
        os.environ["ALLOW_SHELL"] = "true" if data["allow_shell"] else "false"
    if "shell_timeout" in data:
        try:
            os.environ["SHELL_TIMEOUT"] = str(max(1, int(data["shell_timeout"])))
        except (TypeError, ValueError):
            return jsonify({"error": "shell_timeout must be an integer"}), 400
    if "openai_base_url" in data:
        os.environ["OPENAI_BASE_URL"] = str(data["openai_base_url"]).strip()
        with _model_cache_lock:
            _model_cache.pop("openai-compatible", None)
    return api_get_settings()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    provider = os.environ.get("API_PROVIDER", "anthropic")
    default_model = chat_agent.DEFAULT_MODEL_BY_PROVIDER.get(provider, chat_agent.DEFAULT_MODEL)
    model = os.environ.get("MODEL", default_model)

    print()
    print("  Interactive Pydantic Assistant - Web UI")
    print("  ---------------------------------------")
    print(f"  URL      : http://localhost:{PORT}")
    print(f"  Provider : {provider}")
    print(f"  Model    : {model}")
    print(f"  Agent    : {AGENT_DIR}")
    print(f"  Input    : {INPUT_DIR}")
    print(f"  Output   : {OUTPUT_DIR}")
    print("  ---------------------------------------")
    missing = [
        env for prov, env in KEY_ENV_VARS.items()
        if prov not in NO_KEY_PROVIDERS and not os.environ.get(env)
    ]
    if len(missing) >= len(KEY_ENV_VARS) - len(NO_KEY_PROVIDERS):
        print("  NOTE: no API key set -- add one via the web UI or environment.")
    print()

    log.info("Chat assistant starting on %s:%d", HOST, PORT)
    log.info("Provider=%s  Model=%s", provider, model)
    log.info("Agent=%s  Input=%s  Output=%s", AGENT_DIR, INPUT_DIR, OUTPUT_DIR)

    instruction = _read_instruction()
    session.reset(instruction)
    if instruction:
        log.info("instruction.md loaded (%d chars)", len(instruction))
    else:
        log.info("No instruction.md -- create one via the Instructions tab")

    app.run(host=HOST, port=PORT, debug=False, threaded=True)


if __name__ == "__main__":
    main()
