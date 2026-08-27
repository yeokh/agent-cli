"""
LiteLLM CustomLLM implementation that sits between an OpenAI-standard
client and the non-standard backend from mock_backend/server.py.

Architecture this demonstrates:

    OpenAI client --(v1/chat/completions or v1/responses)--> LiteLLM
        --> this CustomLLM handler --(custom headers + custom JSON)-->
        AWS API Gateway --> your custom inference server

Everything OpenAI-format-shaped is handled by LiteLLM itself (both the
/v1/chat/completions and /v1/responses proxy endpoints call into
`completion()` / `streaming()` below and translate their own request and
response shape from/to what this handler returns). This file only has to
know about *your* backend's shape.

Docs: https://docs.litellm.ai/docs/providers/custom_llm_server
"""

import json
import os
import time
from typing import Any, AsyncIterator, Iterator

import httpx
import litellm
from litellm import CustomLLM
from litellm.types.utils import GenericStreamingChunk, ModelResponse, Usage

# --- "API Gateway" configuration -------------------------------------------------
#
# In a real deployment this URL is your AWS API Gateway invoke URL, e.g.
#   https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod/invoke
# and these headers/credentials are whatever the gateway's authorizer expects
# (a usage-plan API key, a Lambda authorizer bearer token, or — if the
# gateway uses IAM auth — a SigV4-signed request, which you'd build here
# with botocore's SigV4Auth instead of a static header).
GATEWAY_URL = os.environ.get("MOCK_BACKEND_URL", "http://127.0.0.1:9000/invoke")
GW_API_KEY = os.environ.get("GW_API_KEY", "gw-demo-key-123")
GW_TENANT_ID = os.environ.get("GW_TENANT_ID", "acme-corp")
GATEWAY_TIMEOUT = float(os.environ.get("MOCK_BACKEND_TIMEOUT", "30"))


def _gateway_headers() -> dict:
    return {
        "X-Gw-Api-Key": GW_API_KEY,
        "X-Tenant-Id": GW_TENANT_ID,
        "Content-Type": "application/json",
    }


def _messages_to_input_text(messages: list) -> str:
    """Collapse OpenAI-style messages into the flat prompt string this
    backend expects. A real backend might want something smarter (e.g. a
    chat template) -- this is the one piece of translation logic that is
    genuinely specific to your server."""
    lines = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, list):
            # handle OpenAI content-part lists (text parts only, for this demo)
            content = " ".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _build_request_body(model: str, messages: list, optional_params: dict, stream: bool) -> dict:
    return {
        "input_text": _messages_to_input_text(messages),
        "params": {
            "max_new_tokens": optional_params.get("max_tokens", 128),
            "temperature": optional_params.get("temperature", 1.0),
            "backend_model": model,
        },
        "stream": stream,
    }


def _to_model_response(model: str, backend_json: dict, model_response: ModelResponse) -> ModelResponse:
    output = backend_json["output"]
    tokens = backend_json["tokens_used"]

    model_response.choices[0].message.content = output["generated_text"]  # type: ignore[union-attr]
    model_response.choices[0].finish_reason = output.get("finish_reason", "stop")
    model_response.model = model
    model_response.usage = Usage(
        prompt_tokens=tokens["input_tokens"],
        completion_tokens=tokens["output_tokens"],
        total_tokens=tokens["total_tokens"],
    )
    return model_response


def _parse_sse_line(line: str) -> dict | None:
    line = line.strip()
    if not line or not line.startswith("data:"):
        return None
    payload = line[len("data:"):].strip()
    if not payload:
        return None
    return json.loads(payload)


class GatewayError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class MyCustomLLM(CustomLLM):
    """Registered under the provider name "my-custom-llm" (see
    proxy/config.yaml). Model strings look like "my-custom-llm/<anything>";
    the suffix is passed through to the backend as "backend_model"."""

    def completion(self, *args, **kwargs) -> ModelResponse:
        model = kwargs["model"]
        messages = kwargs["messages"]
        optional_params = kwargs.get("optional_params", {}) or {}
        model_response = kwargs.get("model_response") or litellm.ModelResponse()

        body = _build_request_body(model, messages, optional_params, stream=False)
        resp = httpx.post(
            GATEWAY_URL, json=body, headers=_gateway_headers(), timeout=GATEWAY_TIMEOUT
        )
        if resp.status_code != 200:
            raise GatewayError(resp.status_code, resp.text)

        return _to_model_response(model, resp.json(), model_response)

    async def acompletion(self, *args, **kwargs) -> ModelResponse:
        model = kwargs["model"]
        messages = kwargs["messages"]
        optional_params = kwargs.get("optional_params", {}) or {}
        model_response = kwargs.get("model_response") or litellm.ModelResponse()

        body = _build_request_body(model, messages, optional_params, stream=False)
        async with httpx.AsyncClient(timeout=GATEWAY_TIMEOUT) as client:
            resp = await client.post(GATEWAY_URL, json=body, headers=_gateway_headers())
        if resp.status_code != 200:
            raise GatewayError(resp.status_code, resp.text)

        return _to_model_response(model, resp.json(), model_response)

    def streaming(self, *args, **kwargs) -> Iterator[GenericStreamingChunk]:
        model = kwargs["model"]
        messages = kwargs["messages"]
        optional_params = kwargs.get("optional_params", {}) or {}

        body = _build_request_body(model, messages, optional_params, stream=True)
        with httpx.stream(
            "POST", GATEWAY_URL, json=body, headers=_gateway_headers(), timeout=GATEWAY_TIMEOUT
        ) as resp:
            if resp.status_code != 200:
                raise GatewayError(resp.status_code, resp.read().decode())
            for line in resp.iter_lines():
                event = _parse_sse_line(line)
                if event is None:
                    continue
                yield _to_generic_chunk(event)

    async def astreaming(self, *args, **kwargs) -> AsyncIterator[GenericStreamingChunk]:
        model = kwargs["model"]
        messages = kwargs["messages"]
        optional_params = kwargs.get("optional_params", {}) or {}

        body = _build_request_body(model, messages, optional_params, stream=True)
        async with httpx.AsyncClient(timeout=GATEWAY_TIMEOUT) as client:
            async with client.stream(
                "POST", GATEWAY_URL, json=body, headers=_gateway_headers()
            ) as resp:
                if resp.status_code != 200:
                    text = await resp.aread()
                    raise GatewayError(resp.status_code, text.decode())
                async for line in resp.aiter_lines():
                    event = _parse_sse_line(line)
                    if event is None:
                        continue
                    yield _to_generic_chunk(event)


def _to_generic_chunk(event: dict) -> GenericStreamingChunk:
    is_finished = bool(event.get("done"))
    usage = event.get("tokens_used") or {}
    return GenericStreamingChunk(
        text=event.get("delta", ""),
        is_finished=is_finished,
        finish_reason=event.get("finish_reason", "") if is_finished else "",
        usage={
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        },
        index=0,
        tool_use=None,
    )


# Instance the proxy config.yaml (and the SDK, if you use it directly)
# points at.
my_custom_llm = MyCustomLLM()
