# tandy-provider

LiteLLM custom provider that wraps the **Tandy (Tandem) legacy LLM API** and
exposes it as a fully OpenAI-compatible interface.

```
OpenAI client --(v1/chat/completions | v1/responses)--> LiteLLM proxy (port 4000)
    --> litellm_provider/custom_handler.py  (translation layer)
    --> Tandy backend  POST /TandemApi  (port 8000)
```

The handler translates:

| OpenAI → Tandy | Tandy → OpenAI |
|----------------|----------------|
| `messages[]` → flattened `message` string | `results.response` → `choices[0].message.content` |
| `system` message → `override_chatprompt` | `results.chat_tokens` → `usage.total_tokens` |
| `model` suffix → `chat_model` key | `results.message_id` → response `id` |
| `temperature` / `max_tokens` → direct | SSE `results.response` chunks → streaming deltas |

## Model names

The proxy exposes standard-looking names that map to Tandy model keys:

| Proxy model name | Tandy `chat_model` key |
|------------------|------------------------|
| `gpt-5-mini`     | `gpt5-mini`            |
| `gpt-4o-mini`    | `gpt4o-mini`           |
| `gpt-4o`         | `gpt4o`                |
| `gpt-4.1`        | `gpt41`                |
| `gpt-4.1-mini`   | `gpt41-mini`           |
| `o3`             | `gpto3`                |
| `o3-mini`        | `gpto3-mini`           |

## Setup

```bash
cd tandy-provider
pip install litellm httpx
```

## Run it

Two processes, each in its own terminal:

**1. The Tandy backend** (from `tandy/`):

```bash
cd ../tandy
export OPENAI_API_KEY="sk-..."
python app.py
```

Listens on `http://localhost:8000`.

**2. The LiteLLM proxy** (from `tandy-provider/`):

```bash
cd tandy-provider
litellm --config proxy/config.yaml --port 4000
```

Listens on `http://localhost:4000`. Demo auth key: `sk-1234`.

## Test it

**Direct curl** (bypasses LiteLLM, hits Tandy directly):

```bash
curl -X POST "http://localhost:8000/TandemApi" \
  -H "Content-Type: application/json" \
  -d '{"userId":"test@example.com","message":"Give me a 1-sentence health tip.","chat_model":"gpt5-mini","streaming":"false"}'
```

**Via LiteLLM proxy** (OpenAI-compatible):

```bash
curl -X POST "http://localhost:4000/v1/chat/completions" \
  -H "Authorization: Bearer sk-1234" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-5-mini","messages":[{"role":"user","content":"Give me a 1-sentence health tip."}]}'
```

curl -X POST "http://localhost:4000/v1/chat/completions" \
  -H "Authorization: Bearer sk-1234" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-5-mini","messages":[{"role":"user","content":"user: Give me a 1-sentence health tip. assistant: Aim for 7–9 hours of quality sleep each night to support immune function, mood regulation, and cognitive performance. user: what else can I do"}]}' | jq


**Python client scripts** (all use the plain `openai` SDK):

```bash
python clients/client_chat_completions.py          # v1/chat/completions, non-streaming
python clients/client_chat_completions_stream.py    # v1/chat/completions, streaming
python clients/client_responses.py                  # v1/responses, non-streaming
python clients/client_responses_stream.py           # v1/responses, streaming
```

## Configuration

All settings are read from environment variables (fall back to safe defaults):

| Variable | Default | Description |
|----------|---------|-------------|
| `TANDY_URL` | `http://localhost:8000/TandemApi` | Full Tandy endpoint URL |
| `TANDY_USER_ID` | `litellm@example.com` | Email sent as `userId` |
| `TANDY_API_KEY` | *(empty)* | Bearer token — omit if not required |
| `TANDY_TIMEOUT` | `60` | HTTP timeout in seconds |

## Adapting to production

- Set `TANDY_URL` to your real Tandy / Tandem API Gateway URL.
- Set `TANDY_USER_ID` to the service-account email your deployment uses.
- Set `TANDY_API_KEY` if the gateway requires an `Authorization` header.
- Replace the demo `master_key` in `proxy/config.yaml` with a secret loaded
  from an environment variable or secrets manager.
