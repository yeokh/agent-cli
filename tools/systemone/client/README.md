# Pydantic AI test clients

These scripts talk to the **local System One gateway** (`http://127.0.0.1:8009`) for decisions. Chat fallback uses a **different** provider endpoint (OpenRouter chat completions).

## Setup

Requires Python 3.11+.

```bash
cd /root/tools/systemone/client
uv venv .venv --python 3.11 && source .venv/bin/activate
uv pip install -r requirements.txt
```

Start the gateway first (see [../README.md](../README.md)).

## Environment

| Variable | Default | Used by |
|---|---|---|
| `SYSTEM_ONE_BASE_URL` | `http://127.0.0.1:8009` | both — local gateway |
| `SYSTEM_ONE_API_KEY` | _(empty)_ | both — only if gateway has `GATEWAY_API_KEY` |
| `SYSTEM_ONE_MODEL` | `jev-latest` | both — model name sent through the gateway |
| `OPENROUTER_API_KEY` | _(required)_ | `chat_fallback.py` — OpenRouter chat |
| `OPENROUTER_CHAT_MODEL` | `openai/gpt-4o-mini` | `chat_fallback.py` |

## Decide (System One only)

```bash
export SYSTEM_ONE_BASE_URL=http://127.0.0.1:8009
python decide_ticket.py
# or:
python decide_ticket.py "I was charged twice. Please refund ASAP."
```

## Chat fallback (System One → OpenRouter chat)

```bash
export SYSTEM_ONE_BASE_URL=http://127.0.0.1:8009
export OPENROUTER_API_KEY=sk-or-...
python chat_fallback.py
```

Decisions go to the local gateway. When the decision model cannot fill a route (e.g. free-form `CustomerReply.body: str`) or the System One call fails, `FallbackModel` uses OpenRouter chat instead.
