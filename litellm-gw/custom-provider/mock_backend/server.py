"""
Stand-in for: (Custom LLM inference server) <-- (AWS API Gateway)

This deliberately does NOT speak OpenAI's v1/completions or v1/chat/completions
schema. It represents "your" backend as described in the scenario:

  - reached through a gateway that injects/requires custom headers
    (here: X-Gw-Api-Key for gateway auth, X-Tenant-Id for a custom
    multi-tenant header some gateways add via a Lambda authorizer / usage
    plan)
  - a single non-standard route (/invoke) instead of /v1/chat/completions
  - a custom request body shape (input_text / params instead of messages)
  - a custom response body shape (output.generated_text instead of
    choices[0].message.content)
  - a custom SSE chunk shape for streaming (delta/done instead of the
    OpenAI chat.completion.chunk delta format)

Run with:
    python mock_backend/server.py
"""

import asyncio
import json
import os
import time

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

app = FastAPI(title="mock-custom-llm-backend")

# Simulates the shared secret / tenant header an AWS API Gateway usage plan
# or Lambda authorizer would enforce in front of the real inference server.
EXPECTED_GW_API_KEY = os.environ.get("GW_API_KEY", "gw-demo-key-123")
EXPECTED_TENANT_ID = os.environ.get("GW_TENANT_ID", "acme-corp")


def _check_gateway_headers(gw_api_key: str | None, tenant_id: str | None) -> None:
    if gw_api_key != EXPECTED_GW_API_KEY:
        raise HTTPException(status_code=403, detail="invalid or missing X-Gw-Api-Key")
    if tenant_id != EXPECTED_TENANT_ID:
        raise HTTPException(status_code=403, detail="invalid or missing X-Tenant-Id")


def _fake_generate(input_text: str, max_new_tokens: int) -> str:
    reply = f"[mock-model] you said: {input_text.strip()!r} (echoing it back, {max_new_tokens} token budget)"
    return reply


@app.post("/invoke")
async def invoke(
    request: Request,
    x_gw_api_key: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
):
    _check_gateway_headers(x_gw_api_key, x_tenant_id)
    body = await request.json()

    input_text = body.get("input_text", "")
    params = body.get("params", {})
    max_new_tokens = int(params.get("max_new_tokens", 128))
    stream = bool(body.get("stream", False))

    generated = _fake_generate(input_text, max_new_tokens)
    prompt_tokens = max(1, len(input_text.split()))
    completion_tokens = max(1, len(generated.split()))

    if not stream:
        return {
            "status": "ok",
            "output": {
                "generated_text": generated,
                "finish_reason": "stop",
            },
            "tokens_used": {
                "input_tokens": prompt_tokens,
                "output_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            "served_at": time.time(),
        }

    async def event_stream():
        words = generated.split(" ")
        for i, word in enumerate(words):
            chunk = {"delta": word + (" " if i < len(words) - 1 else ""), "done": False}
            yield f"data: {json.dumps(chunk)}\n\n"
            await asyncio.sleep(0.05)

        final = {
            "delta": "",
            "done": True,
            "finish_reason": "stop",
            "tokens_used": {
                "input_tokens": prompt_tokens,
                "output_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }
        yield f"data: {json.dumps(final)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9000)
