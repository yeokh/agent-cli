Below is a **step‑by‑step cheat‑sheet** for turning **LiteLLM** into a **single OpenAI‑compatible gateway** that can route requests to **any combination** of the following back‑ends:
- Anthropic (claude‑* models)
- OpenAI (gpt‑*, dall‑e, embeddings, …)
- OpenRouter (any model they expose)
- Ollama (locally‑hosted models)
- vLLM (GPU‑accelerated OpenAI‑compatible server)
- …and any other provider supported by LiteLLM.

The guide is organized into logical sections so you can pick‑and‑choose what applies to your environment (bare‑metal, Docker, Kubernetes, or serverless).

---

## 1️⃣  High‑level Architecture

```
┌───────────────┐          HTTP(s)          ┌─────────────────────┐
│   Client SDK  │  ─────►  LiteLLM Proxy  ◄─►│  Provider 1 (OpenAI)│
│ (curl, openai │  (FastAPI/Starlette)     │ (Anthropic, Ollama, |
│  python, …)   │                           │  vLLM, OpenRouter…)│
└───────────────┘                           └─────────────────────┘
```

- **LiteLLM** runs a tiny FastAPI server that **pretends to be the OpenAI API** (`/v1/chat/completions`, `/v1/completions`, `/v1/embeddings`, …).
- For each incoming request it **looks up a routing rule** → selects a **provider**, **injects the correct API key**, **converts the payload** (if needed) and **calls the provider**.
- The response is translated back to the OpenAI format and returned to the client.

Because LiteLLM works as a **reverse‑proxy**, you do **not** need to change any client code – just point the client’s `api_base` (or `BASE_URL`) to your LiteLLM host.

---

## 2️⃣  Prerequisites

| Item | Minimum version / notes |
|------|--------------------------|
| Python | **3.9+** (3.11 recommended) |
| pip / uv | Latest (`pip install -U pip`) |
| Git | To clone the repo |
| API keys for every provider you intend to use (OpenAI, Anthropic, OpenRouter, …) |
| (Optional) Docker Engine ≥ 20.10 if you want containerised deployment |
| (Optional) `nginx`/`traefik` if you want TLS termination in front of LiteLLM |
| (Optional) a running **vLLM** or **Ollama** instance if you’ll target them locally |

---

## 3️⃣  Install LiteLLM

```bash
# 1️⃣  Clone the repo (or just pip install)
git clone https://github.com/BerriAI/litellm.git
cd litellm

# 2️⃣  Install with all optional extras (covers every provider)
python -m pip install ".[all]"   # includes anthropic, openrouter, ollama, vllm, redis, etc.

# 3️⃣  Verify
litellm --help
```

> **Tip:** If you only need a subset of providers you can install a lighter set: `pip install "litellm[anthropic,openrouter]"`.

---

## 4️⃣  Gather & Store Secrets (API Keys)

LiteLLM can read keys from **environment variables**, a **`.env`** file, or a **secret store** (Redis, Vault, AWS Secrets Manager).
Below is the simplest `.env` method.

Create a file called **`.env`** at the project root:

```dotenv
# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# OpenRouter (use the “default” header key)
OPENROUTER_API_KEY=or-...

# Ollama (no API key needed – address is enough)
OLLAMA_BASE_URL=http://localhost:11434

# vLLM (again no key – just the base URL)
VLLM_BASE_URL=http://localhost:8000/v1

# Optional: global LiteLLM admin key (protects /admin/* endpoints)
LITELLM_MASTER_KEY=super-secret-admin-key

# Optional: telemetries / logging
LITELLM_LOGGING=true
```

> **Security note** – never commit `.env` to source control. Use a secret manager in production.

You can also export them directly in the shell:

```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
# …etc.
```

---

## 5️⃣  Core Configuration File (`config.yaml`)

LiteLLM can be **started with a YAML file** that defines *routing, model‑maps, fallback & rate‑limit policies*.
Create `config.yaml` (or `litellm_config.yaml`) in the same folder:

```yaml
# --------------------------------------------------------------
# 1️⃣  Global settings
# --------------------------------------------------------------
general_settings:
  # Optional: an admin API key to protect /admin/* endpoints
  master_key: ${LITELLM_MASTER_KEY}
  # Enable request/response logging to console or file
  request_logging: true
  # Set a custom request timeout (seconds)
  request_timeout: 180

# --------------------------------------------------------------
# 2️⃣  Provider-level credential defaults (optional, can also use env)
# --------------------------------------------------------------
provider_credentials:
  openai:
    api_key: ${OPENAI_API_KEY}
    base_url: https://api.openai.com/v1
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    base_url: https://api.anthropic.com/v1
  openrouter:
    api_key: ${OPENROUTER_API_KEY}
    base_url: https://openrouter.ai/api/v1
  ollama:
    base_url: ${OLLAMA_BASE_URL}        # e.g. http://localhost:11434
  vllm:
    base_url: ${VLLM_BASE_URL}          # e.g. http://localhost:8000/v1

# --------------------------------------------------------------
# 3️⃣  Model‑to‑provider mapping (the heart of routing)
# --------------------------------------------------------------
model_map:
  # ── OpenAI hosted models ───────────────────────
  gpt-4: openai
  gpt-3.5-turbo: openai
  # ── Anthropic models ───────────────────────────
  claude-2: anthropic
  claude-instant-1: anthropic
  # ── OpenRouter (you can use any of their names) ─────
  meta-llama/Meta-Llama-3-8B-Instruct: openrouter
  mistralai/mistral-7b-instruct-v0.1: openrouter
  # ── Local Ollama models (the name you gave Ollama) ─────
  llama2: ollama
  mixtral: ollama
  # ── vLLM deployed model names ───────────────────────
  my-vllm-phi: vllm
  my-gemma-2b: vllm

# --------------------------------------------------------------
# 4️⃣  Routing rules – you can also route by **path** or **headers**
# --------------------------------------------------------------
router:
  # Route based on the `model` field (the default behaviour)
  default_route: model

  # Advanced: Route based on an HTTP header `x-provider`
  #   e.g. curl -H "x-provider: anthropic" …
  header_route:
    X-Provider:
      openai: openai
      anthropic: anthropic
      openrouter: openrouter
      ollama: ollama
      vllm: vllm

# --------------------------------------------------------------
# 5️⃣  Fallback (optional) – try another provider if primary fails
# --------------------------------------------------------------
fallbacks:
  # Try OpenAI if Anthropic returns a 5xx error
  anthropic: [openai]
  # If Ollama is down, fall back to OpenRouter
  ollama: [openrouter]

# --------------------------------------------------------------
# 6️⃣  Rate‑limit & quota (simple token‑bucket) – per‑api‑key
# --------------------------------------------------------------
rate_limits:
  # 1000 requests per API key per hour
  per_key:
    limit: 1000
    period: 3600

# --------------------------------------------------------------
# 7️⃣  Caching (optional) – store cheap completions in Redis
# --------------------------------------------------------------
cache:
  type: redis
  redis_url: redis://localhost:6379/0
  ttl_seconds: 300   # cache entries live 5 min

# --------------------------------------------------------------
# 8️⃣  Telemetry / Monitoring (optional)
# --------------------------------------------------------------
observability:
  enabled: true
  # works with Prometheus; expose /metrics endpoint
  prometheus_port: 9090
```

**Key concepts**

| Section | What it does |
|---------|--------------|
| `provider_credentials` | Supplies each backend’s API key & custom base URL (e.g. Ollama runs on `localhost:11434`). |
| `model_map` | **Directs a model name** to a provider. If a client asks for `model="claude-2"` LiteLLM knows to forward to Anthropic. |
| `router` | Determines **how the routing decision is made** – by model name, by an extra header, or even a query‑parameter. |
| `fallbacks` | Transparent retry on a different provider when the primary returns an error (5xx, timeout, or a specific `error_code`). |
| `rate_limits` / `cache` | Optional production goodies – per‑key QPS limits, response caching, etc. |
| `observability` | Exposes a Prometheus `/metrics` endpoint for Grafana/K8s monitoring. |

> **You can omit any block you don’t need** – LiteLLM will fall back to its defaults (environment variables, no fallback, no caching, etc.).

---

## 6️⃣  Starting the Proxy

### 6.1 Run locally (quick‑start)

```bash
# Make sure the .env is loaded (pipenv/venv, or export manually)
export $(cat .env | xargs)

# Start the server – by default it reads `litellm_config.yaml` in cwd
litellm --config ./config.yaml --port 4000
```

You’ll see a log similar to:

```
2024-09-10 12:34:56,789 INFO     Starting LiteLLM proxy
2024-09-10 12:34:56,790 INFO     Listening on http://0.0.0.0:4000
2024-09-10 12:34:56,791 INFO     Loaded 8 providers, 27 model mappings
```

#### Verify with `curl`

```bash
# OpenAI‑style request routed to Anthropic (model=claude-2)
curl http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
        "model": "claude-2",
        "messages": [{"role":"user","content":"Hello, Claude!"}]
      }'
```

You should receive a JSON response that looks exactly like an OpenAI chat completion, even though the request was handled by Anthropic.

### 6.2 Docker‑Compose (recommended for dev / simple prod)

Create `docker-compose.yml`:

```yaml
version: "3.9"
services:
  litellm:
    image: ghcr.io/berriai/litellm:latest   # official image
    container_name: litellm
    ports:
      - "4000:4000"
    env_file:
      - .env                               # inject all secrets
    volumes:
      - ./config.yaml:/app/litellm_config.yaml:ro
      - ./cache:/app/cache                 # optional persistent cache
    command: >
      litellm --config /app/litellm_config.yaml
    restart: unless-stopped

  # Optional: Redis for caching/rate‑limit persistence
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped
```

Start it:

```bash
docker compose up -d
```

The proxy is now reachable at **`http://localhost:4000`**.

---

## 7️⃣  Deploying to Production

Below are three common patterns; pick the one that fits your infra.

| Target                     | TL;DR steps |
|----------------------------|-------------|
| **Kubernetes (Helm)**      | Use the community Helm chart `litellm` (or create one). Set `values.yaml` with `envFrom` to secret references. |
| **AWS Elastic Beanstalk / ECS** | Build a Docker image (`Dockerfile` below), push to ECR, then run the task behind an ALB with TLS termination. |
| **Serverless (Cloud Functions / Vercel)** | LiteLLM is a FastAPI app – you can wrap it with `Mangum` for AWS Lambda or `vercel-python`. Performance is limited; use for low‑traffic/dev. |

### 7.1 Minimal Dockerfile (if you want to customise)

```dockerfile
FROM python:3.11-slim

# Install runtime dependencies (git, curl if you need them)
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Copy only required files first (caching layers)
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install --no-cache-dir ".[all]"

# Copy source & config
COPY litellm ./litellm
COPY config.yaml ./
COPY .env ./

EXPOSE 4000
CMD ["litellm", "--config", "./config.yaml", "--port", "4000"]
```

Build & push:

```bash
docker build -t myorg/litellm:latest .
docker push myorg/litellm:latest
```

### 7.2 TLS & Host‑header handling

If you terminate TLS **outside** (NGINX/Traefik/Cloud‑LB) you typically just:

```nginx
server {
    listen 443 ssl;
    server_name ai-gateway.mycompany.com;

    ssl_certificate /etc/ssl/certs/fullchain.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;

    location / {
        proxy_pass http://litellm:4000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

No changes to LiteLLM are required – it will pick up the `Host` header automatically (helpful if you embed the hostname in telemetry).

---

## 8️⃣  Advanced Router Features

### 8.1 Route by **HTTP Header** (multi‑tenant scenario)

Add the following to `router.header_route` (already shown in the config example) and then:

```bash
curl http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Provider: openrouter" \
  -d '{"model":"meta-llama/Meta-Llama-3-8B-Instruct","messages":[{"role":"user","content":"Explain LLMs"}]}'
```

The `X-Provider` header **overrides** the `model_map`. This is handy when you want to let a tenant explicitly pick a provider regardless of model name.

### 8.2 Route by **query string** (`?provider=openai`)

Add to `router`:

```yaml
query_route:
  provider:
    openai: openai
    anthropic: anthropic
    ollama: ollama
    vllm: vllm
```

Now:

```
GET /v1/models?provider=openai
```

### 8.3 **Dynamic model‑map** via environment variable

If you want to switch providers without redeploying, you can store `model_map` in a **Redis hash** and set `router.dynamic_map=true`. LiteLLM will fetch the hash on each request (cached for 5 seconds). Example:

```yaml
router:
  dynamic_map: true
  redis_url: redis://redis:6379/1   # the hash key is `model_map`
```

You can then update at runtime:

```bash
redis-cli HSET model_map "gpt-3.5-turbo" "openrouter"
```

### 8.4 **Fallback customizing**

You can specify **error‑type based** fallbacks:

```yaml
fallbacks:
  anthropic:
    - provider: openai
      errors: [RateLimitedError, ServiceUnavailableError]   # only on those errors
```

### 8.5 **Prompt‑pre‑processing / post‑processing hooks**

LiteLLM supports **callbacks** (`pre_call`, `post_call`) in Python. Write a tiny plugin:

```python
# callbacks.py
from litellm import CallbackHandler

class MyCallback(CallbackHandler):
    async def async_pre_call(self, model, messages, **kwargs):
        # Example: prepend a system prompt for every request
        system = {"role": "system", "content": "You are a helpful assistant."}
        if messages[0]["role"] != "system":
            messages.insert(0, system)
        return model, messages, kwargs

    async def async_post_call(self, response, **kwargs):
        # Example: strip out any leading newline characters
        response["choices"][0]["message"]["content"] = response["choices"][0]["message"]["content"].lstrip()
        return response

# expose to LiteLLM via env var
LITELLM_CALLBACKS=callbacks.MyCallback
```

Add to `.env`:

```dotenv
LITELLM_CALLBACKS=callbacks.MyCallback
```

When the server starts it will import the class and run it on every request.

---

## 9️⃣  Testing & Validation

### 9.1 Built‑in health endpoint

```
GET http://localhost:4000/health
```

Returns:

```json
{"status":"healthy","uptime_seconds":32}
```

### 9.2 Provider‑specific health checks (optional)

If you enable `observability.enabled`, you can also hit:

```
GET http://localhost:4000/provider_status
```

It attempts a **lightweight ping** to each configured provider and returns a map:

```json
{
  "openai": "ok",
  "anthropic": "ok",
  "ollama": "timeout",
  "vllm": "ok"
}
```

### 9.3 Unit‑test sample (pytest)

```python
import httpx, pytest

BASE = "http://localhost:4000/v1"

@pytest.mark.parametrize("model,provider", [
    ("gpt-4", "openai"),
    ("claude-2", "anthropic"),
    ("llama2", "ollama"),
])
def test_routing(model, provider):
    payload = {"model": model, "messages": [{"role":"user","content":"ping"}]}
    r = httpx.post(f"{BASE}/chat/completions", json=payload, timeout=30)
    assert r.status_code == 200
    # the provider name appears in the `LiteLLM-Provider` response header
    assert r.headers.get("LiteLLM-Provider") == provider
```

Run:

```bash
pytest -q
```

If all pass, your routing logic is sound.

---

## 10️⃣  Production‑Ready Extras

| Feature | How to enable | Why it matters |
|---------|---------------|----------------|
| **Prometheus metrics** | `observability.enabled: true` + `prometheus_port: 9090` | Allows you to monitor request latency per provider, error rates, cache hit ratio, etc. |
| **Structured logging** | `LITELLM_LOG_FORMAT=json` env var | Makes logs ingestable by ELK/Datadog. |
| **IP‑allowlist** | `allowed_ip_ranges: ["10.0.0.0/8","203.0.113.0/24"]` in config | Prevents random internet traffic from abusing your gateway. |
| **Per‑tenant quotas** | Use the **`client_identity`** header (`X-Client-ID`) + `rate_limits.per_key` | Guarantees one tenant cannot hog all calls. |
| **Retry policy** | `retry_policy: {max_attempts: 3, backoff_factor: 0.5}` | Handles transient errors (e.g., 502 from Anthropic). |
| **Circuit breaker** | `circuit_breaker: {failure_threshold: 5, reset_seconds: 120}` | Stops hammering a flaky provider. |
| **Tracing (OpenTelemetry)** | Set `OTEL_EXPORTER_OTLP_ENDPOINT` and enable `observability.tracing: true` | Gives you distributed traces from your client through LiteLLM to the downstream provider. |

All the above are **optional** – you can add them later without redeploying the code (most are read from environment variables at startup).

---

## 11️⃣  Common Pitfalls & Debugging Tips

| Symptom | Likely cause | Quick fix |
|---------|--------------|-----------|
| `401 Unauthorized` from LiteLLM even though provider keys are set | The environment variable name is wrong or not exported. | `echo $OPENAI_API_KEY` → ensure non‑empty. |
| Model not found (`model: "gpt-4" – error: Invalid model`) | `model_map` does not contain the model or you forgot the provider mapping. | Add `gpt-4: openai` under `model_map`. |
| Request hangs > 30 s | Provider URL unreachable (e.g., Ollama not started) or firewall blocks. | `curl http://localhost:11434` → sanity‑check. |
| `LiteLLM-Provider` header missing | You started LiteLLM with `--no-include-headers` flag (rare). | Run without that flag or set `include_provider_header: true`. |
| Rate‑limit errors even though you have a high quota | The **global** `rate_limits` block is applied per *LiteLLM API key*, not per downstream provider. | Increase `limit` or disable rate limiting (`rate_limits: {}`) for testing. |
| vLLM returns `Invalid URL` | You forgot to add `/v1` at the end of `VLLM_BASE_URL`. | Ensure base URL ends with `/v1` (or set `vllm.base_url: http://localhost:8000/v1`). |
| OpenRouter models return `model_not_found` | The model name must be **exact** as OpenRouter catalogued it. Use their UI or `/models` endpoint to copy. | `curl https://openrouter.ai/api/v1/models` → pick a valid name. |

You can also increase log verbosity at runtime:

```bash
export LITELLM_LOG_LEVEL=DEBUG
litellm --config ./config.yaml
```

All request/response bodies (truncated at 2 KB) are printed, making it trivial to see whether the payload conversion is correct.

---

## 12️⃣  Full Example – End‑to‑End Walkthrough

Below is a **complete, copy‑pasteable** setup that you can run on a fresh machine:

```bash
# 1️⃣  Create a new folder
mkdir llm-gateway && cd llm-gateway

# 2️⃣  Create .env (replace keys)
cat > .env <<'EOF'
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=or-...
OLLAMA_BASE_URL=http://host.docker.internal:11434   # Docker‑for‑Mac/Windows convenience
VLLM_BASE_URL=http://host.docker.internal:8000/v1
LITELLM_MASTER_KEY=admin-secret
EOF

# 3️⃣  Write config.yaml (copy the YAML from section 5)
cat > config.yaml <<'EOF'
general_settings:
  master_key: ${LITELLM_MASTER_KEY}
  request_logging: true
provider_credentials:
  openai:
    api_key: ${OPENAI_API_KEY}
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
  openrouter:
    api_key: ${OPENROUTER_API_KEY}
  ollama:
    base_url: ${OLLAMA_BASE_URL}
  vllm:
    base_url: ${VLLM_BASE_URL}
model_map:
  gpt-4: openai
  claude-2: anthropic
  meta-llama/Meta-Llama-3-8B-Instruct: openrouter
  llama2: ollama
  phi-2: vllm
router:
  default_route: model
fallbacks:
  ollama: [openrouter, openai]
rate_limits:
  per_key:
    limit: 5000
    period: 3600
EOF

# 4️⃣  Pull the LiteLLM Docker image
docker pull ghcr.io/berriai/litellm:latest

# 5️⃣  Run the container
docker run -d \
  --name litellm-gw \
  -p 4000:4000 \
  --env-file .env \
  -v "$(pwd)/config.yaml:/app/litellm_config.yaml:ro" \
  ghcr.io/berriai/litellm:latest \
  litellm --config /app/litellm_config.yaml --port 4000

# 6️⃣  Test – OpenAI route
curl http://localhost:4000/v1/models | jq .
# Should list all the models you mapped (gpt-4, claude-2, llama2, …)

# 7️⃣  Test – Anthropic route
curl http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-2","messages":[{"role":"user","content":"Tell me a joke"}]}' | jq .
```

You now have a **single endpoint** (`http://localhost:4000/v1`) that any OpenAI‑compatible client can call, and under the hood each request is steered to its proper vendor.

---

## 13️⃣  TL;DR Checklist (Copy‑Paste to Notepad)

```
[ ] Install Python ≥3.9 + pip
[ ] pip install "litellm[all]"
[ ] Create .env with all provider keys
[ ] Write config.yaml (model_map + provider_credentials)
[ ] Choose deployment mode (local, Docker, K8s)
[ ] Start LiteLLM (`litellm --config config.yaml --port 4000`)
[ ] Verify health endpoint (`GET /health`)
[ ] Test a few models with curl
[ ] (Optional) Add rate‑limit, caching, prometheus, TLS
[ ] Deploy to prod with Docker/K8s + secret management
[ ] Monitor /metrics and logs
```

That’s it! 🎉 You now have a **robust, production‑ready, multi‑provider LLM gateway** powered by **LiteLLM**. Feel free to extend the config with more providers, custom routing logic, or even a UI dashboard – the core concepts stay the same. Happy prompting! 🚀

