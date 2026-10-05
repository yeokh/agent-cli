# Local System One Gateway

A single-container gateway that exposes a TypeSafe-compatible **System One** API:

- `POST /v1/systemone` — evaluate `state` against typed `noul` / `choice` / `score` questions
- `GET /v1/models` — curated (or upstream) model list
- `GET /healthz` — liveness

Pydantic AI and the TypeSafe SDK talk to **this** gateway. The gateway forwards to an upstream that already speaks System One (OpenRouter Jev, local Kev, Ollama decision models, Unsloth Laya, etc.).

---

## Quick Start

### Build

```bash
cd /root/tools/systemone
podman build -t systemone-gateway:latest .
```

### Run with OpenRouter (default)

```bash
podman run --rm -p 8009:8009 \
  -e UPSTREAM_BASE_URL=https://openrouter.ai/api \
  -e UPSTREAM_API_KEY="$OPENROUTER_API_KEY" \
  -e DEFAULT_MODEL=jev-latest \
  systemone-gateway:latest
```

### Run without a container (dev)

Requires Python 3.11+.

```bash
cd /root/tools/systemone
uv venv .venv --python 3.11 && source .venv/bin/activate
uv pip install -r requirements.txt
export UPSTREAM_BASE_URL=https://openrouter.ai/api
export UPSTREAM_API_KEY="$OPENROUTER_API_KEY"
export PYTHONPATH=.
uvicorn app.main:app --host 0.0.0.0 --port 8009
```

### Curl smoke test

```bash
curl -s localhost:8009/v1/systemone -H 'content-type: application/json' -d '{
  "state": "Shoes arrived two weeks late and in the wrong size. Also I see two charges on my card.",
  "model": "jev-latest",
  "questions": {
    "department":  {"type": "choice", "instructions": "Which team should handle this?",
                    "criteria": {"returns": "Exchanges, refunds, wrong or damaged items",
                                 "shipping": "Delivery status, delays, lost packages",
                                 "billing": "Charges, invoices, payment problems"}},
    "escalate":    {"type": "noul",  "instructions": "Does this need urgent human attention?"},
    "frustration": {"type": "score", "instructions": "How frustrated is the customer?",
                    "criteria": ["Calm", "Frustrated", "Very angry"]}
  }
}'
```

---

## Upstream backends

| Upstream | `UPSTREAM_BASE_URL` | Typical `DEFAULT_MODEL` | API key |
|---|---|---|---|
| OpenRouter (Jev) | `https://openrouter.ai/api` | `jev-latest` | `UPSTREAM_API_KEY=$OPENROUTER_API_KEY` |
| Local Kev | `http://host.containers.internal:8010` (or host IP) | `kev-latest` | omit / empty |
| Local Ollama decision models | `http://host.containers.internal:11434` | `nimble` | omit / empty |
| Unsloth Laya | `http://host.containers.internal:8888` | `laya` | Unsloth token if required |

Swap upstreams by changing env vars only — clients keep pointing at `http://localhost:8009`.

### Local Kev example

If Kev already listens on host port `8010`:

```bash
podman run --rm -p 8009:8009 \
  -e UPSTREAM_BASE_URL=http://host.containers.internal:8010 \
  -e DEFAULT_MODEL=kev-latest \
  systemone-gateway:latest
```

### Local Ollama example

```bash
podman run --rm -p 8009:8009 \
  -e UPSTREAM_BASE_URL=http://host.containers.internal:11434 \
  -e DEFAULT_MODEL=nimble \
  systemone-gateway:latest
```

---

## Environment

| Variable | Default | Meaning |
|---|---|---|
| `UPSTREAM_BASE_URL` | `https://openrouter.ai/api` | Origin of the System One provider (with or without trailing `/v1`) |
| `UPSTREAM_API_KEY` | _(empty)_ | Bearer token sent upstream |
| `DEFAULT_MODEL` | `jev-latest` | Inserted when the request omits `model` |
| `LISTEN_HOST` | `0.0.0.0` | Bind address |
| `LISTEN_PORT` | `8009` | Bind port |
| `GATEWAY_API_KEY` | _(empty)_ | If set, clients must send `Authorization: Bearer …` |
| `UPSTREAM_TIMEOUT_S` | `60` | Upstream HTTP timeout |
| `CURATED_MODELS` | _(built-in list)_ | Comma-separated names for `GET /v1/models` fallback |

---

## Pydantic AI test client

See [`client/README.md`](client/README.md). The client talks to **this gateway** for decisions; chat fallback uses a **different** provider (OpenRouter chat completions).
