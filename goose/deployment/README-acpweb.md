# Goose ACP Web UI — Container & OpenShift Deployment

Run [acp-web.py](../acp-web.py) as a containerised Flask web UI for the Goose ACP server on OpenShift (or locally with Podman).

The container spawns a `goose acp` subprocess and exposes a browser UI on port **8082**.

## Files

| File | Purpose |
|------|---------|
| `Containerfile-acpweb` | Image build definition |
| `entrypoint-acpweb.sh` | Container entrypoint — sets up dirs and launches Flask |
| `openshift/acpweb-pvc.yaml` | Two PVCs: goose config (1 Gi) and workspace (5 Gi) |
| `openshift/acpweb-secret.yaml` | Reference template for the API keys Secret |
| `openshift/acpweb-deployment.yaml` | Deployment — mounts PVCs, loads keys from Secret |
| `openshift/acpweb-service.yaml` | ClusterIP Service on port 8082 |
| `openshift/acpweb-route.yaml` | HTTPS Route with edge TLS termination |

## Supported Providers

Goose supports 15+ providers. The table below lists the ones most commonly used via environment variables / Secrets.

| Provider | `GOOSE_PROVIDER` value | API key env var | Notes |
|----------|------------------------|-----------------|-------|
| OpenAI | `openai` | `OPENAI_API_KEY` | |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` | |
| Google Gemini | `google` | `GOOGLE_API_KEY` | |
| **OpenRouter** | **`openrouter`** | **`OPENROUTER_API_KEY`** | Unified gateway to 200+ models |
| Azure OpenAI | `azure` | `AZURE_OPENAI_API_KEY` | Requires `AZURE_OPENAI_ENDPOINT` |
| AWS Bedrock | `bedrock` | AWS credential chain | |
| Ollama | `ollama` | _(none)_ | Set `OLLAMA_HOST` |

### OpenRouter

[OpenRouter](https://openrouter.ai/) is a unified API gateway that gives access to 200+ models from OpenAI, Anthropic, Google, Meta, Mistral, and others under a single API key. Use it to avoid managing multiple provider keys or to enable automatic failover across models.

**Environment variables:**

| Variable | Description | Example |
|----------|-------------|---------|
| `GOOSE_PROVIDER` | Select OpenRouter | `openrouter` |
| `GOOSE_MODEL` | Model to use (OpenRouter model ID) | `anthropic/claude-sonnet-4-5` |
| `OPENROUTER_API_KEY` | Your OpenRouter API key | `sk-or-v1-...` |
| `OPENROUTER_PARAMETERS` *(optional)* | Extra OpenRouter request params (JSON or YAML) | see below |

**Popular models available via OpenRouter:**

```
openai/gpt-4o
openai/gpt-5.4-nano
anthropic/claude-sonnet-4-5
anthropic/claude-haiku-4.5
google/gemini-2.5-pro
meta-llama/llama-3.3-70b-instruct
mistralai/mistral-large
```

**Advanced parameters** (`OPENROUTER_PARAMETERS`): pass a JSON string to control OpenRouter-specific fields such as reasoning effort, verbosity, or plugins without touching goose's own request fields:

```bash
export OPENROUTER_PARAMETERS='{"reasoning": {"effort": "high"}, "plugins": [{"id": "web"}]}'
```

---

## 1. Build and push the image

Run from the `goose/` directory:

```bash
export IMAGE=quay.io/kenghua_yeo/goose-acpweb:v1

podman build -t "${IMAGE}" -f deployment/Containerfile-acpweb .
podman login quay.io
podman push "${IMAGE}"
```

---

## 2. Test locally with Podman

Create named volumes (once):

```bash
podman volume create goose-acpweb-config
podman volume create goose-acpweb-workspace
```

Run with **OpenAI**:

```bash
podman run --rm -p 8082:8082 \
  -e GOOSE_PROVIDER=openai \
  -e GOOSE_MODEL=gpt-4o \
  -e OPENAI_API_KEY=sk-... \
  -v goose-acpweb-config:/home/goose/.config/goose \
  -v goose-acpweb-workspace:/home/goose/workspace \
  quay.io/kenghua_yeo/goose-acpweb:v1
```

Run with **OpenRouter** (access any model through one key):

```bash
podman run --rm -p 8082:8082 \
  -e GOOSE_PROVIDER=openrouter \
  -e GOOSE_MODEL=anthropic/claude-sonnet-4-5 \
  -e OPENROUTER_API_KEY=sk-or-v1-... \
  -v goose-acpweb-config:/home/goose/.config/goose \
  -v goose-acpweb-workspace:/home/goose/workspace \
  quay.io/kenghua_yeo/goose-acpweb:v1
```

Open **http://localhost:8082** in your browser.

Use a local directory as the workspace instead of a volume:

```bash
podman run --rm -p 8082:8082 \
  -e GOOSE_PROVIDER=openrouter \
  -e GOOSE_MODEL=openai/gpt-4o \
  -e OPENROUTER_API_KEY=sk-or-v1-... \
  -v goose-acpweb-config:/home/goose/.config/goose \
  -v "$PWD/myproject:/home/goose/workspace:Z" \
  quay.io/kenghua_yeo/goose-acpweb:v1
```

Test with /bin/bash:
podman run -it --rm -p 8082:8082     -e OPENAI_API_KEY=sk-proj-   -e GOOSE_PROVIDER=openai     -e GOOSE_MODEL=gpt-5.4-nano     -v goose-config:/home/goose/.config/goose     -v goose-workspace:/home/goose/workspace --entrypoint /bin/bash    quay.io/kenghua_yeo/goose-acpweb:v1


---

## 3. Deploy on OpenShift

### 3a. Log in and select a project

```bash
oc login <api-server-url>
oc new-project goose          # or: oc project <existing-project>
```

### 3b. Create the API keys Secret

Use `oc create secret` to avoid storing keys in YAML files:

**OpenAI:**
```bash
oc create secret generic goose-acpweb-api-keys \
  --from-literal=GOOSE_PROVIDER=openai \
  --from-literal=GOOSE_MODEL=gpt-4o \
  --from-literal=OPENAI_API_KEY=sk-...
```

**Anthropic:**
```bash
oc create secret generic goose-acpweb-api-keys \
  --from-literal=GOOSE_PROVIDER=anthropic \
  --from-literal=GOOSE_MODEL=claude-sonnet-4-5 \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-...
```

**OpenRouter** (single key, choose any model at deploy time):
```bash
oc create secret generic goose-acpweb-api-keys \
  --from-literal=GOOSE_PROVIDER=openrouter \
  --from-literal=GOOSE_MODEL=anthropic/claude-sonnet-4-5 \
  --from-literal=OPENROUTER_API_KEY=sk-or-v1-...
```

### 3c. Apply storage, deployment, service, and route

```bash
oc apply -f deployment/openshift/acpweb-pvc.yaml
oc apply -f deployment/openshift/acpweb-deployment.yaml
oc apply -f deployment/openshift/acpweb-service.yaml
oc apply -f deployment/openshift/acpweb-route.yaml
```

Wait for the pod to be ready:

```bash
oc get pod -l app=goose-acpweb -w
```

Get the URL:

```bash
oc get route goose-acpweb
```

Open the printed hostname in your browser (HTTPS).

### 3d. If the Quay repository is private

```bash
oc create secret docker-registry quay-pull-secret \
  --docker-server=quay.io \
  --docker-username=<quay-username> \
  --docker-password=<quay-password>

oc secrets link default quay-pull-secret --for=pull
```

---

## 4. Switch model or provider without rebuilding

Update the Secret and restart the pod — no image rebuild required:

```bash
oc create secret generic goose-acpweb-api-keys \
  --from-literal=GOOSE_PROVIDER=openrouter \
  --from-literal=GOOSE_MODEL=openai/o3 \
  --from-literal=OPENROUTER_API_KEY=sk-or-v1-... \
  --dry-run=client -o yaml | oc apply -f -

oc rollout restart deployment/goose-acpweb
```

---

## 5. Persistent storage

| Volume mount | PVC | What it holds |
|--------------|-----|---------------|
| `/home/goose/.config/goose` | `goose-acpweb-config` | Provider config, session history |
| `/home/goose/workspace` | `goose-acpweb-workspace` | Working files the agent reads/writes |

Both PVCs survive pod restarts and redeployments. Delete them only when you want to wipe state:

```bash
oc delete pvc goose-acpweb-config goose-acpweb-workspace
```

---

## 6. Redeploy a new image

```bash
export IMAGE=quay.io/kenghua_yeo/goose-acpweb:v1

podman build -t "${IMAGE}" -f deployment/Containerfile-acpweb .
podman push "${IMAGE}"

oc rollout restart deployment/goose-acpweb
oc rollout status  deployment/goose-acpweb
```

---

## Environment variable reference

| Variable | Default in image | Description |
|----------|-----------------|-------------|
| `GOOSE_PROVIDER` | _(none — set via Secret)_ | Active provider |
| `GOOSE_MODEL` | _(none — set via Secret)_ | Model name |
| `GOOSE_MODE` | `smart_approve` | Tool approval mode |
| `GOOSE_DISABLE_KEYRING` | `1` | Required in containers (no system keyring) |
| `GOOSE_TELEMETRY_OFF` | `1` | Disable telemetry |
| `PORT` | `8082` | Flask listen port |
| `OPENAI_API_KEY` | _(none)_ | OpenAI API key |
| `ANTHROPIC_API_KEY` | _(none)_ | Anthropic API key |
| `GOOGLE_API_KEY` | _(none)_ | Google Gemini API key |
| `OPENROUTER_API_KEY` | _(none)_ | OpenRouter API key |
| `OPENROUTER_PARAMETERS` | _(none)_ | Extra OpenRouter request params (JSON) |

---

## Troubleshooting

### Pod not starting

```bash
oc describe pod -l app=goose-acpweb
oc logs -l app=goose-acpweb
```

### Secret missing or wrong key name

```bash
oc get secret goose-acpweb-api-keys -o yaml
```

### Goose session fails to start (provider not configured)

The pod will start but the web UI will show "Session not ready". Check that `GOOSE_PROVIDER` and the matching API key are both set in the Secret and that the key is valid. Click **Reconnect** in the UI after fixing the Secret and restarting the pod.

### Permission errors on config directory

The image is built for OpenShift's arbitrary UID (group 0, `g+rwX` on `/home/goose`). Confirm the PVC is mounted at `/home/goose/.config/goose` as in `openshift/acpweb-deployment.yaml`.

### Cannot reach the LLM API from the cluster

Confirm cluster egress allows HTTPS to your provider endpoint (`api.openai.com`, `api.anthropic.com`, `openrouter.ai`, etc.). Check corporate proxies and NetworkPolicies.
