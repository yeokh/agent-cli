# LiteLLM Proxy Gateway: End-to-End Deployment Guide (Rootless Podman Edition)

Below is a **step-by-step cheat-sheet** for turning **LiteLLM** into a **single OpenAI-compatible gateway** running as a **rootless container via Podman**. It routes requests to **any combination** of backends:
- Anthropic (claude-* models)
- OpenAI (gpt-*, dall-e, embeddings, …)
- OpenRouter (any model they expose)
- Ollama (locally-hosted models)
- vLLM (GPU-accelerated OpenAI-compatible server)
- …and any other provider supported by LiteLLM.

---

## 1️⃣  High-Level Architecture

```text
┌───────────────┐          HTTP(s)          ┌─────────────────────┐
│   Client SDK  │  ─────►  LiteLLM Proxy  ◄─►│  Provider 1 (OpenAI)│
│ (curl, openai │  (Podman Rootless Container│ (Anthropic, Ollama, |
│  python, …)   │   listening on port 4000) │  vLLM, OpenRouter…) │
└───────────────┘                          └─────────────────────┘
```

- **LiteLLM** runs as a unprivileged container process managed by **Podman**.
- It translates incoming OpenAI-formatted requests into provider-native payloads and handles credential injection.
- Because LiteLLM acts as a **reverse-proxy**, client applications only need their `base_url` repointed to your LiteLLM server.

---

## 2️⃣  Prerequisites

| Item | Minimum version / notes |
|------|--------------------------|
| Podman | **4.0+** running in **rootless mode** (`podman info` -> `rootless: true`) |
| podman-compose | (Optional) if using compose files (`pip install podman-compose` or `podman-compose`) |
| API keys | For external providers (OpenAI, Anthropic, OpenRouter) |
| Local AI | Running **vLLM** or **Ollama** instances on host or in adjacent containers |

---

## 3️⃣  Gather & Store Secrets (API Keys)

LiteLLM securely references environment variables using `os.environ/` syntax in `config.yaml`.

Create a file called **`.env`** at the project root:

```dotenv
# Cloud Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=or-...

# Local Providers (Using Podman's host DNS alias)
OLLAMA_BASE_URL=http://host.containers.internal:11434
VLLM_BASE_URL=http://host.containers.internal:8000/v1

# Admin Key
LITELLM_MASTER_KEY=super-secret-admin-key
```

> **Rootless Podman Note:** Use `host.containers.internal` instead of `host.docker.internal` or `localhost` to reach services running on the host network outside the container.

---

## 4️⃣  Core Configuration File (`config.yaml`)

Create `config.yaml` in the same directory:

```yaml
# --------------------------------------------------------------
# 1️⃣  Global Proxy Settings
# --------------------------------------------------------------
general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  request_logging: true

# --------------------------------------------------------------
# 2️⃣  Model-to-Provider Mapping
# --------------------------------------------------------------
model_list:
  # ── Cloud Models ────────────────────────────────
  - model_name: gpt-4
    litellm_params:
      model: openai/gpt-4
      api_key: os.environ/OPENAI_API_KEY

  - model_name: claude-2
    litellm_params:
      model: anthropic/claude-2
      api_key: os.environ/ANTHROPIC_API_KEY

  - model_name: meta-llama/Meta-Llama-3-8B-Instruct
    litellm_params:
      model: openrouter/meta-llama/Meta-Llama-3-8B-Instruct
      api_key: os.environ/OPENROUTER_API_KEY

  # ── Local Models (Ollama & vLLM via host.containers.internal) ─
  - model_name: llama2
    litellm_params:
      model: ollama/llama2
      api_base: os.environ/OLLAMA_BASE_URL

  - model_name: my-vllm-phi
    litellm_params:
      model: hosted_vllm/phi-2
      api_base: os.environ/VLLM_BASE_URL
      api_key: "none"

# --------------------------------------------------------------
# 3️⃣  Processing & Router Settings
# --------------------------------------------------------------
litellm_settings:
  drop_params: true 

router_settings:
  routing_strategy: simple-shuffle
  fallbacks:
    - {"claude-2": ["gpt-4"]}
    - {"llama2": ["meta-llama/Meta-Llama-3-8B-Instruct"]}
```

---

## 5️⃣  Running with Rootless Podman

### Option A: Podman CLI (`podman run`)

Ensure SELinux mounts are permitted by appending the `:z` or `:ro,z` volume flags if running on SELinux-enabled distributions (Fedora, RHEL, CentOS):

```bash
podman run -d   --name litellm-gw   --user 1000:1000   -p 4000:4000   --env-file .env   -v "$(pwd)/config.yaml:/app/config.yaml:ro,z"   ghcr.io/berriai/litellm:latest   --config /app/config.yaml --port 4000
```

*Note: Do NOT run this with `sudo`. Execute it directly under your standard unprivileged user account.*

### Option B: Podman Compose

Create `compose.yaml`:

```yaml
version: "3.8"
services:
  litellm:
    image: ghcr.io/berriai/litellm:latest
    container_name: litellm
    ports:
      - "4000:4000"
    env_file:
      - .env
    volumes:
      - ./config.yaml:/app/config.yaml:ro,z
    command: >
      --config /app/config.yaml --port 4000
    restart: unless-stopped
```

Run without root privileges:
```bash
podman-compose up -d
# OR using Podman 4.5+ built-in compose provider:
podman compose up -d
```

---

## 6️⃣  Testing & Verification

```bash
# Check container status
podman ps

# Send test request to LiteLLM Gateway
curl http://localhost:4000/v1/chat/completions   -H "Content-Type: application/json"   -H "Authorization: Bearer super-secret-admin-key"   -d '{
        "model": "claude-2",
        "messages": [{"role":"user","content":"Hello, Claude!"}]
      }'
```

---

## 7️⃣  Rootless & Podman Specific Pitfalls

| Symptom | Cause | Solution |
|---------|-------|----------|
| `Permission denied` when mounting `config.yaml` | SELinux security context blocking rootless access. | Append `:z` or `:ro,z` to volume flag (`-v ./config.yaml:/app/config.yaml:ro,z`). |
| `Connection refused` when connecting to local Ollama / vLLM | Using `localhost` or `127.0.0.1` inside container targets container's loopback, not host. | Use `http://host.containers.internal:11434` or `http://host.containers.internal:8000/v1`. |
| Container stops when SSH session closes | Systemd user session terminates upon logout. | Enable lingering for your unprivileged user: `loginctl enable-linger $USER`. |
| Cannot bind port `<1024` | Unprivileged users cannot bind privileged ports by default. | Use a non-privileged port like `4000` (default) or adjust `net.ipv4.ip_unprivileged_port_start`. |

---

## 8️⃣  Complete Rootless Walkthrough Script

Copy-paste this directly into your terminal as a standard user (**without `sudo`**):

```bash
# 1️⃣  Create working directory
mkdir -p ~/llm-gateway && cd ~/llm-gateway

# 2️⃣  Create .env file
cat > .env <<'EOF'
OPENAI_API_KEY=sk-abc123xyz
ANTHROPIC_API_KEY=sk-ant-abc123xyz
OPENROUTER_API_KEY=or-abc123xyz
OLLAMA_BASE_URL=http://host.containers.internal:11434
LITELLM_MASTER_KEY=admin-secret
EOF

# 3️⃣  Create config.yaml
cat > config.yaml <<'EOF'
general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY

model_list:
  - model_name: gpt-4
    litellm_params:
      model: openai/gpt-4
      api_key: os.environ/OPENAI_API_KEY
  - model_name: claude-2
    litellm_params:
      model: anthropic/claude-2
      api_key: os.environ/ANTHROPIC_API_KEY
  - model_name: llama2
    litellm_params:
      model: ollama/llama2
      api_base: os.environ/OLLAMA_BASE_URL

litellm_settings:
  drop_params: true

router_settings:
  routing_strategy: simple-shuffle
  fallbacks:
    - {"claude-2": ["gpt-4"]}
EOF

# 4️⃣  Run container with Podman (rootless)
podman run -d   --name litellm-gw   -p 4000:4000   --env-file .env   -v "$(pwd)/config.yaml:/app/config.yaml:ro,z"   ghcr.io/berriai/litellm:latest   --config /app/config.yaml --port 4000

# 5️⃣  Enable lingering so container stays running after SSH disconnects
loginctl enable-linger $USER

# 6️⃣  Test the proxy
curl http://localhost:4000/v1/chat/completions   -H "Content-Type: application/json"   -H "Authorization: Bearer admin-secret"   -d '{"model":"claude-2","messages":[{"role":"user","content":"Say hello!"}]}'
```
