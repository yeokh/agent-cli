# Goose ttyd Web Terminal — Container & OpenShift Deployment

Run [Goose](https://github.com/block/goose) as an interactive web terminal on OpenShift (or locally with Podman) using [ttyd](https://github.com/tsl0922/ttyd).

The container launches `ttyd` serving a `goose session` and exposes a browser-accessible terminal on port **7681**.

## Files

| File | Purpose |
|------|---------|
| `Containerfile-ttyd` | Image build definition |
| `openshift/ttyd-pvc.yaml` | Two PVCs: goose config (1 Gi) and workspace (5 Gi) |
| `openshift/ttyd-secret.yaml` | Reference template for the API keys Secret |
| `openshift/ttyd-deployment.yaml` | Deployment — mounts PVCs, loads keys from Secret |
| `openshift/ttyd-service.yaml` | ClusterIP Service on port 7681 |
| `openshift/ttyd-route.yaml` | HTTPS Route with edge TLS termination |

## Supported Providers

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

[OpenRouter](https://openrouter.ai/) is a unified API gateway that gives access to 200+ models from OpenAI, Anthropic, Google, Meta, Mistral, and others under a single API key.

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

---

## 1. Build and push the image

Run from the `goose/` directory:

```bash
export IMAGE=quay.io/kenghua_yeo/goose-ttyd:v1

podman build -t "${IMAGE}" -f deployment/Containerfile-ttyd .
podman login quay.io
podman push "${IMAGE}"
```

---

## 2. Test locally with Podman

Create named volumes (once):

```bash
podman volume create goose-ttyd-config
podman volume create goose-ttyd-workspace
```

Run with **OpenAI**:

```bash
podman run --rm -p 7681:7681 \
  -e GOOSE_PROVIDER=openai \
  -e GOOSE_MODEL=gpt-4o \
  -e OPENAI_API_KEY=sk-... \
  -v goose-ttyd-config:/home/goose/.config/goose \
  -v goose-ttyd-workspace:/home/goose/workspace \
  quay.io/kenghua_yeo/goose-ttyd:v1
```

Run with **Anthropic**:

```bash
podman run --rm -p 7681:7681 \
  -e GOOSE_PROVIDER=anthropic \
  -e GOOSE_MODEL=claude-sonnet-4-5 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -v goose-ttyd-config:/home/goose/.config/goose \
  -v goose-ttyd-workspace:/home/goose/workspace \
  quay.io/kenghua_yeo/goose-ttyd:v1
```

Run with **OpenRouter** (single key, choose any model):

```bash
podman run --rm -p 7681:7681 \
  -e GOOSE_PROVIDER=openrouter \
  -e GOOSE_MODEL=anthropic/claude-sonnet-4-5 \
  -e OPENROUTER_API_KEY=sk-or-v1-... \
  -v goose-ttyd-config:/home/goose/.config/goose \
  -v goose-ttyd-workspace:/home/goose/workspace \
  quay.io/kenghua_yeo/goose-ttyd:v1
```

Open **http://localhost:7681** in your browser.

Use a local directory as the workspace instead of a volume:

```bash
podman run --rm -p 7681:7681 \
  -e GOOSE_PROVIDER=openrouter \
  -e GOOSE_MODEL=openai/gpt-4o \
  -e OPENROUTER_API_KEY=sk-or-v1-... \
  -v goose-ttyd-config:/home/goose/.config/goose \
  -v "$PWD/myproject:/home/goose/workspace:Z" \
  quay.io/kenghua_yeo/goose-ttyd:v1
```

Debug with an interactive shell:

```bash
podman run -it --rm -p 7681:7681 \
  -e GOOSE_PROVIDER=openai \
  -e GOOSE_MODEL=gpt-4o \
  -e OPENAI_API_KEY=sk-... \
  -v goose-ttyd-config:/home/goose/.config/goose \
  -v goose-ttyd-workspace:/home/goose/workspace \
  --entrypoint /bin/bash \
  quay.io/kenghua_yeo/goose-ttyd:v1
```

Copy files to running pod:
oc cp ~/agent-jobs/ansible-playbook-builder/input  goose-ttyd-cc4d9bfb7-4p8rd:/home/goose/workspace/input

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
oc create secret generic goose-ttyd-api-keys \
  --from-literal=GOOSE_PROVIDER=openai \
  --from-literal=GOOSE_MODEL=gpt-4o \
  --from-literal=OPENAI_API_KEY=sk-...
```

**Anthropic:**
```bash
oc create secret generic goose-ttyd-api-keys \
  --from-literal=GOOSE_PROVIDER=anthropic \
  --from-literal=GOOSE_MODEL=claude-sonnet-4-5 \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-...
```

**OpenRouter** (single key, choose any model at deploy time):
```bash
oc create secret generic goose-ttyd-api-keys \
  --from-literal=GOOSE_PROVIDER=openrouter \
  --from-literal=GOOSE_MODEL=anthropic/claude-sonnet-4-5 \
  --from-literal=OPENROUTER_API_KEY=sk-or-v1-...
```

### 3c. Apply storage, deployment, service, and route

```bash
oc apply -f deployment/openshift/ttyd-pvc.yaml
oc apply -f deployment/openshift/ttyd-deployment.yaml
oc apply -f deployment/openshift/ttyd-service.yaml
oc apply -f deployment/openshift/ttyd-route.yaml
```

Wait for the pod to be ready:

```bash
oc get pod -l app=goose-ttyd -w
```

Get the URL:

```bash
oc get route goose-ttyd
```

Open the printed hostname in your browser (HTTPS) to access the Goose terminal.

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
oc create secret generic goose-ttyd-api-keys \
  --from-literal=GOOSE_PROVIDER=openrouter \
  --from-literal=GOOSE_MODEL=openai/o3 \
  --from-literal=OPENROUTER_API_KEY=sk-or-v1-... \
  --dry-run=client -o yaml | oc apply -f -

oc rollout restart deployment/goose-ttyd
```

---

## 5. Persistent storage

| Volume mount | PVC | What it holds |
|--------------|-----|---------------|
| `/home/goose/.config/goose` | `goose-ttyd-config` | Provider config, session history |
| `/home/goose/workspace` | `goose-ttyd-workspace` | Working files the agent reads/writes |

Both PVCs survive pod restarts and redeployments. Delete them only when you want to wipe state:

```bash
oc delete pvc goose-ttyd-config goose-ttyd-workspace
```

---

## 6. Redeploy a new image

```bash
export IMAGE=quay.io/kenghua_yeo/goose-ttyd:v1

podman build -t "${IMAGE}" -f deployment/Containerfile-ttyd .
podman push "${IMAGE}"

oc rollout restart deployment/goose-ttyd
oc rollout status  deployment/goose-ttyd
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
| `OPENAI_API_KEY` | _(none)_ | OpenAI API key |
| `ANTHROPIC_API_KEY` | _(none)_ | Anthropic API key |
| `GOOGLE_API_KEY` | _(none)_ | Google Gemini API key |
| `OPENROUTER_API_KEY` | _(none)_ | OpenRouter API key |

---

## Troubleshooting

### Pod not starting

```bash
oc describe pod -l app=goose-ttyd
oc logs -l app=goose-ttyd
```

### Secret missing or wrong key name

```bash
oc get secret goose-ttyd-api-keys -o yaml
```

### Browser connects but terminal shows no output

ttyd starts the `goose session` command inside the terminal. If Goose fails to initialise (e.g. missing or invalid API key), the terminal will open but show an error message. Fix the Secret and restart the pod:

```bash
oc rollout restart deployment/goose-ttyd
```

### Permission errors on config directory

The image runs as uid 1001 with group 0 (`g+rwX` on `/home/goose`), which satisfies OpenShift's arbitrary UID policy. Confirm the PVC is mounted at `/home/goose/.config/goose` as in `openshift/ttyd-deployment.yaml`.

### Cannot reach the LLM API from the cluster

Confirm cluster egress allows HTTPS to your provider endpoint (`api.openai.com`, `api.anthropic.com`, `openrouter.ai`, etc.). Check corporate proxies and NetworkPolicies.
