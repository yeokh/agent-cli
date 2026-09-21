# litellm-custom-provider

Example of wrapping a non-standard LLM backend with LiteLLM so that any
OpenAI-standard client can talk to it over `v1/chat/completions` and
`v1/responses`, streaming and non-streaming.

```
OpenAI client --(v1/chat/completions | v1/responses)--> LiteLLM proxy
    --> litellm_provider/custom_handler.py (translation + custom headers)
    --> "API Gateway"  (mock_backend/server.py stands in for this)
    --> your custom inference server
```

`mock_backend/server.py` simulates *your* backend: it requires custom
headers (`X-Gw-Api-Key`, `X-Tenant-Id` -- stand-ins for whatever your real
AWS API Gateway usage plan / Lambda authorizer / IAM SigV4 requires), lives
at a non-standard route (`/invoke`), and speaks a completely custom JSON
shape for both the normal response and the SSE stream. It is **not**
OpenAI-compatible on purpose, to mirror the scenario.

`litellm_provider/custom_handler.py` is the only piece that knows how to
translate between the two: it subclasses `litellm.CustomLLM` and implements
`completion` / `acompletion` / `streaming` / `astreaming`, adding the
gateway's custom headers and reshaping request/response bodies each way.
See https://docs.litellm.ai/docs/providers/custom_llm_server for the
interface this implements.

## Setup

```bash
cd C:\DevWorks\ws-ai\litellm-custom-provider
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run it

Three processes, in order, each in its own terminal (all from the project root):

**1. The mock "custom backend behind API Gateway":**

```bash
python mock_backend/server.py
```

Listens on `http://127.0.0.1:9000`.

**2. The LiteLLM proxy** (translates OpenAI-standard requests into calls
against the mock backend via the custom handler):

```bash
litellm --config proxy/config.yaml --port 4000
```

Listens on `http://localhost:4000`. Auth is the demo master key `sk-1234`
set in `proxy/config.yaml`.

**3. Any of the client examples:**

```bash
python clients/client_chat_completions.py          # v1/chat/completions, non-streaming
python clients/client_chat_completions_stream.py    # v1/chat/completions, streaming
python clients/client_responses.py                  # v1/responses, non-streaming
python clients/client_responses_stream.py           # v1/responses, streaming
```

All four use the plain `openai` Python SDK pointed at the LiteLLM proxy
(`base_url="http://localhost:4000"`) -- from the client's point of view this
is indistinguishable from talking to OpenAI directly. The `v1/responses`
examples work without any extra config: LiteLLM bridges the Responses API
to the same underlying `completion()`/`streaming()` calls for providers
(including custom ones) that don't natively implement it.

## Adapting this to your real backend

- Point `MOCK_BACKEND_URL` (env var read in `litellm_provider/custom_handler.py`)
  at your real AWS API Gateway invoke URL instead of the mock server.
- Replace `_gateway_headers()` in `custom_handler.py` with whatever your
  gateway actually needs. A static API key header is shown; if your gateway
  uses IAM auth instead, sign the request with `botocore`'s `SigV4Auth` in
  that same function rather than a static header.
- Replace `_build_request_body`, `_to_model_response`, and `_to_generic_chunk`
  in `custom_handler.py` with the actual request/response shapes your
  inference server uses -- that's the entire translation layer.
- `GW_API_KEY` / `GW_TENANT_ID` / `MOCK_BACKEND_URL` are read from the
  environment (see the top of `custom_handler.py`); set them before starting
  the proxy instead of relying on the demo defaults.
