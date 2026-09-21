"""
LiteLLM CustomLLM implementation that bridges an OpenAI-standard client to
the Tandy (Tandem) legacy LLM API.

Architecture:

    OpenAI client --(v1/chat/completions | v1/responses)--> LiteLLM proxy
        --> this CustomLLM handler (translation layer)
        --> Tandy backend  POST /TandemApi

Tandy request shape:
    {
        "userId":             <email>,          # required
        "message":            <string>,         # full prompt / conversation history
        "chat_model":         <model key>,      # e.g. "gpt5-mini", "gpt4o-mini"
        "override_chatprompt":<string|null>,    # system prompt
        "temperature":        <float|null>,
        "max_token":          <int|null>,
        "streaming":          "true"|"false"
    }

Tandy non-streaming response:
    { "results": { "response": <text>, "chat_tokens": <int>, "message_id": <uuid>, ... } }

Tandy streaming response (SSE):
    data: { "results": { "response": <chunk>, "message_id": <uuid>, ... } }
    data: { "results": { "response": <chunk>, ... } }
    ...  (stream ends without a [DONE] sentinel)

Docs: https://docs.litellm.ai/docs/providers/custom_llm_server
"""

import json
import os
from typing import Any, AsyncIterator, Iterator

import httpx
import litellm
from litellm import CustomLLM
from litellm.types.utils import GenericStreamingChunk, ModelResponse, Usage

# ---------------------------------------------------------------------------
# Configuration (all overridable via environment variables)
# ---------------------------------------------------------------------------

TANDY_URL = os.environ.get("TANDY_URL", "http://localhost:8000/TandemApi")
TANDY_USER_ID = os.environ.get("TANDY_USER_ID", "litellm@example.com")
TANDY_TIMEOUT = float(os.environ.get("TANDY_TIMEOUT", "60"))

# Optional bearer token / API key forwarded to Tandy.  Set to "" to omit.
TANDY_API_KEY = os.environ.get("TANDY_API_KEY", "")


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _tandy_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if TANDY_API_KEY:
        headers["Authorization"] = f"Bearer {TANDY_API_KEY}"
    return headers


def _extract_system_and_message(messages: list) -> tuple[str | None, str]:
    """
    Split OpenAI-style messages into:
    - system_prompt  (the last system message, or None)
    - message        (multi-turn conversation flattened as Tandy expects)

    Multi-turn format Tandy accepts:
        "User: ...\nAssistant: ...\nUser: ..."
    Single-turn (just a user message) is passed as-is.
    """
    system_prompt: str | None = None
    conversation_parts: list[str] = []

    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")

        # Flatten content-part lists (vision / multi-modal; text parts only)
        if isinstance(content, list):
            content = " ".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            )

        if role == "system":
            system_prompt = content          # last system message wins
        elif role == "user":
            conversation_parts.append(f"User: {content}")
        elif role == "assistant":
            conversation_parts.append(f"Assistant: {content}")

    # If there is only a single user turn, send just the raw content (no prefix)
    # so simple single-message calls look clean in Tandy logs.
    if len(conversation_parts) == 1 and conversation_parts[0].startswith("User: "):
        message = conversation_parts[0][len("User: "):]
    else:
        message = "\n".join(conversation_parts)

    return system_prompt, message


# Parameters the Tandy backend understands.  Everything else is dropped so
# that calls from the Responses API (which injects reasoning_effort, etc.)
# or tool-calling clients don't cause a 400 from Tandy.
_TANDY_SUPPORTED_PARAMS = {"temperature", "max_tokens"}


def _build_tandy_request(
    model: str, messages: list, optional_params: dict, stream: bool
) -> dict:
    system_prompt, message = _extract_system_and_message(messages)

    # Strip any params Tandy does not accept (e.g. reasoning_effort,
    # tool_choice, parallel_tool_calls injected by the Responses API layer).
    params = {k: v for k, v in (optional_params or {}).items() if k in _TANDY_SUPPORTED_PARAMS}

    body: dict[str, Any] = {
        "userId": TANDY_USER_ID,
        "message": message,
        "chat_model": model,          # suffix after "tandy/" passed straight through
        "streaming": "true" if stream else "false",
    }

    if system_prompt is not None:
        body["override_chatprompt"] = system_prompt

    temperature = params.get("temperature")
    if temperature is not None:
        body["temperature"] = temperature

    max_tokens = params.get("max_tokens")
    if max_tokens is not None:
        body["max_token"] = max_tokens

    return body


def _to_model_response(
    model: str, tandy_json: dict, model_response: ModelResponse
) -> ModelResponse:
    results = tandy_json.get("results", {})
    text = results.get("response", "")
    total_tokens = results.get("chat_tokens", 0)
    message_id = results.get("message_id", "")

    model_response.choices[0].message.content = text          # type: ignore[union-attr]
    model_response.choices[0].finish_reason = "stop"
    model_response.model = model
    if message_id:
        model_response.id = f"chatcmpl-{message_id}"
    model_response.usage = Usage(
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=total_tokens,
    )
    return model_response


def _parse_sse_line(line: str) -> dict | None:
    line = line.strip()
    if not line or not line.startswith("data:"):
        return None
    payload = line[len("data:"):].strip()
    if not payload or payload == "[DONE]":
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def _event_to_generic_chunk(event: dict, is_finished: bool = False) -> GenericStreamingChunk:
    results = event.get("results", {})
    text = results.get("response", "")
    return GenericStreamingChunk(
        text=text,
        is_finished=is_finished,
        finish_reason="stop" if is_finished else "",
        usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        index=0,
        tool_use=None,
    )


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------

class TandyError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


# ---------------------------------------------------------------------------
# CustomLLM implementation
# ---------------------------------------------------------------------------

class TandyCustomLLM(CustomLLM):
    """
    Registered under the provider name "tandy" (see proxy/config.yaml).
    Model strings look like "tandy/<chat_model_key>", e.g. "tandy/gpt5-mini".
    The suffix is forwarded verbatim to Tandy as the `chat_model` field.

    Tandy model keys:
        gpt4o, gpt4o-mini, gpt41, gpt41-mini,
        gpt5, gpt5-mini, gpto3, gpto3-mini
    """

    # ------------------------------------------------------------------ sync

    def completion(self, *args, **kwargs) -> ModelResponse:
        model = kwargs["model"]
        messages = kwargs["messages"]
        optional_params = kwargs.get("optional_params", {}) or {}
        model_response = kwargs.get("model_response") or litellm.ModelResponse()

        body = _build_tandy_request(model, messages, optional_params, stream=False)
        resp = httpx.post(TANDY_URL, json=body, headers=_tandy_headers(), timeout=TANDY_TIMEOUT)
        if resp.status_code != 200:
            raise TandyError(resp.status_code, resp.text)

        return _to_model_response(model, resp.json(), model_response)

    def streaming(self, *args, **kwargs) -> Iterator[GenericStreamingChunk]:
        model = kwargs["model"]
        messages = kwargs["messages"]
        optional_params = kwargs.get("optional_params", {}) or {}

        body = _build_tandy_request(model, messages, optional_params, stream=True)
        last_chunk: GenericStreamingChunk | None = None

        with httpx.stream(
            "POST", TANDY_URL, json=body, headers=_tandy_headers(), timeout=TANDY_TIMEOUT
        ) as resp:
            if resp.status_code != 200:
                raise TandyError(resp.status_code, resp.read().decode())

            lines = list(resp.iter_lines())          # buffer so we know which is last

        # Yield all but the last content chunk without is_finished; mark last True
        content_events = [_parse_sse_line(l) for l in lines]
        content_events = [e for e in content_events if e is not None]

        for i, event in enumerate(content_events):
            is_last = i == len(content_events) - 1
            yield _event_to_generic_chunk(event, is_finished=is_last)

        # Ensure we always emit at least one finished chunk (empty stream edge-case)
        if not content_events:
            yield GenericStreamingChunk(
                text="", is_finished=True, finish_reason="stop",
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                index=0, tool_use=None,
            )

    # --------------------------------------------------------------- async

    async def acompletion(self, *args, **kwargs) -> ModelResponse:
        model = kwargs["model"]
        messages = kwargs["messages"]
        optional_params = kwargs.get("optional_params", {}) or {}
        model_response = kwargs.get("model_response") or litellm.ModelResponse()

        body = _build_tandy_request(model, messages, optional_params, stream=False)
        async with httpx.AsyncClient(timeout=TANDY_TIMEOUT) as client:
            resp = await client.post(TANDY_URL, json=body, headers=_tandy_headers())
        if resp.status_code != 200:
            raise TandyError(resp.status_code, resp.text)

        return _to_model_response(model, resp.json(), model_response)

    async def astreaming(self, *args, **kwargs) -> AsyncIterator[GenericStreamingChunk]:
        model = kwargs["model"]
        messages = kwargs["messages"]
        optional_params = kwargs.get("optional_params", {}) or {}

        body = _build_tandy_request(model, messages, optional_params, stream=True)

        async with httpx.AsyncClient(timeout=TANDY_TIMEOUT) as client:
            async with client.stream(
                "POST", TANDY_URL, json=body, headers=_tandy_headers()
            ) as resp:
                if resp.status_code != 200:
                    text = await resp.aread()
                    raise TandyError(resp.status_code, text.decode())

                # Buffer lines to mark the last one as finished
                lines: list[str] = []
                async for line in resp.aiter_lines():
                    lines.append(line)

        content_events = [_parse_sse_line(l) for l in lines]
        content_events = [e for e in content_events if e is not None]

        for i, event in enumerate(content_events):
            is_last = i == len(content_events) - 1
            yield _event_to_generic_chunk(event, is_finished=is_last)

        if not content_events:
            yield GenericStreamingChunk(
                text="", is_finished=True, finish_reason="stop",
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                index=0, tool_use=None,
            )


# Instance that proxy/config.yaml references
tandy_custom_llm = TandyCustomLLM()
