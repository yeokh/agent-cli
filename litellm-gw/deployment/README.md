# LiteLLM Gateway — Deployment Guide

A containerised **OpenAI-compatible LLM proxy** built on [LiteLLM](https://github.com/BerriAI/litellm).  
Routes requests to multiple providers through a single endpoint, using the `ghcr.io/berriai/litellm-non_root` image (runs as non-root, compatible with OpenShift's restricted SCC out of the box).

---

## Architecture

```
                        ┌─────────────────────────────┐
                        │     LiteLLM Gateway Pod      │
                        │  (litellm-non_root:latest)   │
Client SDK              │                              │
(curl / openai-python)  │  config.yaml (ConfigMap)     │──► OpenAI          :443
        │               │  secrets    (Secret → env)   │──► Anthropic       :443
        ▼               │                              │──► OpenRouter       :443
  port 4000  ──────────►│  /v1/chat/completions        │──► Red Hat MaaS    :443
  Bearer: master_key    │  /v1/models                  │──► vLLM in-cluster :8000
                        │  /health/readiness            │
                        └─────────────────────────────┘
```

All secrets are injected as environment variables and referenced in `config.yaml` via LiteLLM's native `os.environ/<VAR>` syntax — no secrets are stored in the ConfigMap or image.

---

## File Structure

```
deployment/
├── .env.example                   # Template — copy to .env for local/podman use
├── config.yaml                    # LiteLLM model routing config (os.environ/ refs)
├── run.sh                         # Rootless Podman start/stop/logs script
├── download-tiktoken-cache.sh     # One-time script to pre-download BPE tokenizer files
├── deploy-litellm-secrets.yaml    # OpenShift Secret (fill in values before apply)
├── deploy-litellm.yaml            # OpenShift ConfigMap + Deployment + Service + Route
├── networkpolicy-litellm-gw.yaml  # OpenShift NetworkPolicy (ingress + egress)
└── README.md                      # This file

../tiktoken_cache/                 # BPE encoding files (created by download-tiktoken-cache.sh)
```

---

## Configured Providers & Models

| Provider | Models | Auth |
|---|---|---|
| **OpenAI** | `gpt-5.4-nano`, `gpt-5-mini`, `gpt-5-nano` | `OPENAI_API_KEY` |
| **Anthropic** | `claude-haiku-4-5` | `ANTHROPIC_API_KEY` |
| **OpenRouter** | `openrouter/claude-haiku-4.5`, `openrouter/gpt-5.4-nano`, `openrouter/gpt-5-mini` | `OPENROUTER_API_KEY` |
| **Red Hat MaaS** | `qwen3-14b`, `gpt-oss-20b`, `gpt-oss-120b` | `REDHAT_API_KEY` |
| **vLLM** (local) | `vllm/local` | none |

To add or change models edit `config.yaml` (local) or the `litellm-config` ConfigMap in `deploy-litellm.yaml` (OpenShift).

---

## Option A — Rootless Podman (`run.sh`)

### Prerequisites
- Podman 4.0+ in rootless mode (`podman info | grep rootless`)
- The `ghcr.io/berriai/litellm-non_root:latest` image already pulled

### Steps

```bash
cd /root/litellm-gw/deployment

# 1. Create your .env from the template
cp .env.example .env
vim .env          # fill in all API keys and VLLM_MODEL

# 2. Start the container
./run.sh          # starts in detached mode

# 3. Follow logs
./run.sh logs

# 4. Stop the container
./run.sh stop
```

> **Tip:** Run `loginctl enable-linger $USER` once to keep the container alive after SSH logout.

### Local Providers (vLLM / Ollama)

Use `host.containers.internal` in `.env` to reach services running on the host:

```dotenv
VLLM_BASE_URL=http://host.containers.internal:8000/v1
```

---

## Option B — OpenShift

### Prerequisites
- `oc` CLI logged in to your cluster
- Pull secret or image already cached (the `litellm-non_root` image is public on ghcr.io)

### Deploy

```bash
# 1. Create the project (once)
oc new-project litellm-gw

# 2. Fill in secrets — edit the file before applying
vim deploy-litellm-secrets.yaml
oc apply -f deploy-litellm-secrets.yaml

# 3. Deploy ConfigMap, Deployment, Service, and Route
oc apply -f deploy-litellm.yaml

# 4. Apply NetworkPolicy (restricts ingress/egress — see below)
oc apply -f networkpolicy-litellm-gw.yaml

# 5. Confirm rollout
oc rollout status deployment/litellm-gw -n litellm-gw

# 6. Get the public HTTPS URL
oc get route litellm-gw-route -n litellm-gw
```

Service or Route:
curl http://litellm-gw-service.kenghua-yeo-dev.svc.cluster.local:4000/v1/models -H 'Authorization: Bearer sk-321WV4d3DClo6je'

curl https://litellm-gw-route-kenghua-yeo-dev.apps.rm3.7wse.p1.openshiftapps.com/v1/models -H 'Authorization: Bearer sk-321WV4d3DClo6je'



### Update config or secrets

```bash
# Edit the ConfigMap and trigger a rolling restart
oc edit configmap litellm-config -n litellm-gw
oc rollout restart deployment/litellm-gw -n litellm-gw

# Rotate a secret value
oc edit secret litellm-secret -n litellm-gw   # values are base64 in data:
oc rollout restart deployment/litellm-gw -n litellm-gw
```

### Clean up

```bash
oc delete networkpolicy,route,svc,deploy,configmap,secret --all -n litellm-gw
oc delete project litellm-gw
```

---

## Network Policy

`networkpolicy-litellm-gw.yaml` locks down the `litellm-gw` namespace to only what is required.

### Ingress (allowed → pod port 4000)

| Source | Selector used | Why |
|---|---|---|
| OpenShift router | `network.openshift.io/policy-group: ingress` | Serves the public Route |
| Same-namespace pods | `podSelector: {}` | Health checks, co-located tooling |

All other inbound traffic is denied by default.

### Egress (allowed from pod)

| Destination | Port | Protocol | Why |
|---|---|---|---|
| OpenShift DNS (`openshift-dns`) | 53 | UDP + TCP | Name resolution for all upstreams |
| External public IPs (non-RFC-1918) | 443 | TCP | OpenAI, Anthropic, OpenRouter, Red Hat MaaS |
| vLLM in-cluster pod | 8000 | TCP | Local GPU inference |

RFC-1918 ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) are **excluded** from the HTTPS rule to prevent lateral movement within the cluster network.

> **FQDN filtering:** Standard Kubernetes NetworkPolicy matches on IPs, not hostnames.  
> The HTTPS rule covers all non-private IPs on port 443. If you need per-domain egress restrictions (e.g. only `api.openai.com`), add an OpenShift **EgressFirewall** object alongside this policy.

### Adjusting the vLLM egress rule

If your vLLM pod is in a different namespace or has different labels, edit the last egress block in `networkpolicy-litellm-gw.yaml`:

```yaml
- to:
  - namespaceSelector:
      matchLabels:
        kubernetes.io/metadata.name: <your-vllm-namespace>
    podSelector:
      matchLabels:
        app: <your-vllm-pod-label>
  ports:
  - protocol: TCP
    port: 8000
```

If vLLM is outside the cluster entirely, remove that block — it is already reachable via port 443 (or adjust to the correct port).

---

## Testing

In wsl, podman port bind to WSL VM's external interface instead of the loopback interface, 127.0.0.1, that Windows automatally forwards to 'localhost' from Windows.  To test from within wsl, get the wsl VM's IP address... use "ip addr show eth0 | grep inet" instead of 127.0.0.1.

curl http://10.208.69.173:4000/v1/chat/completions -H 'Content-Type: application/json' -H 'Authorization: Bearer sk-321WV4d3DClo6je'  -d '{"model":"gpt-oss-120b","messages":[{"role":"user","content":"Hello!"}]}' | jq '.choices[].message.content'


curl https://litellm-gw-route-kenghua-yeo-dev.apps.rm3.7wse.p1.openshiftapps.com/v1/chat/completions \
     -H 'Authorization: Bearer sk-321WV4d3DClo6je' \
     -H 'Content-Type: application/json' \
     -d '{
       "model": "gpt-5.4-nano",
       "messages": [{"role": "user", "content": "Hello, how are you?"}]
     }' | jq '.choices[].message.content'



### List available models

```bash
# Podman
curl http://localhost:4000/v1/models \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" | jq '.data[].id'

# OpenShift (replace with your Route hostname)
ROUTE=$(oc get route litellm-gw-route -n litellm-gw -o jsonpath='{.spec.host}')
curl https://$ROUTE/v1/models \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" | jq '.data[].id'
```

### Chat completion

```bash
curl https://$ROUTE/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -d '{
    "model": "gpt-5-mini",
    "messages": [{"role": "user", "content": "Hello! Respond in one word."}]
  }'
```

### Health endpoints

```bash
curl https://$ROUTE/health/readiness
curl https://$ROUTE/health/liveliness
```

---

## Startup Performance Tuning

LiteLLM startup time grows with the number of model entries in `config.yaml`. The following settings (already applied) address each bottleneck.

### Environment variables

Set in `.env` (Podman) or the Deployment spec (OpenShift):

| Variable | Value | Effect |
|---|---|---|
| `LITELLM_TELEMETRY` | `False` | Disables BerriAI analytics — belt-and-suspenders with `config.yaml` |
| `DISABLE_TELEMETRY` | `True` | Secondary telemetry flag read before config is parsed |
| `DISABLE_UI` | `True` | Skips loading the web dashboard assets and routes |
| `TIKTOKEN_CACHE_DIR` | `/tmp/tiktoken_cache` | Points tiktoken to the pre-downloaded local BPE files (see below) |

### config.yaml settings

| Setting | Section | Value | Effect |
|---|---|---|---|
| `telemetry: false` | `litellm_settings` | `false` | Eliminates synchronous HTTP call to BerriAI analytics servers |
| `health_check_interval: 300` | `general_settings` only | 300 s | Background health probes run every 5 min; without this LiteLLM probes all model endpoints sequentially at boot |
| `request_timeout: 30` | `litellm_settings` | 30 s | Caps probe hang time — a single unreachable endpoint can otherwise stall for ~2 min |
| `enable_pre_call_checks: false` | `router_settings` | `false` | Uses cached health state instead of re-checking before every request |

### Tiktoken local cache

LiteLLM uses [tiktoken](https://github.com/openai/tiktoken) to count tokens. Without a local cache it fetches BPE encoding files (~6.8 MB total) from `openaipublic.blob.core.windows.net` on first use of each model family.

**Run once** on the host to pre-download all standard encodings:

```bash
cd /root/litellm-gw/deployment
./download-tiktoken-cache.sh
# Files saved to /root/litellm-gw/tiktoken_cache/
```

| Encoding | Models covered | Size |
|---|---|---|
| `cl100k_base` | GPT-4, GPT-3.5-turbo, text-embedding-ada-002 | ~816 KB |
| `o200k_base` | GPT-4o, GPT-4o-mini | ~1.6 MB |
| `p50k_base` | text-davinci-002/003, code-davinci-002 | ~817 KB |
| `r50k_base` | GPT-3 (davinci, curie, babbage, ada) | ~3.5 MB |

- **Podman** — `run.sh` automatically mounts `../tiktoken_cache` into the container at `/tmp/tiktoken_cache` (read-only). It warns and continues if the cache directory is missing.
- **OpenShift** — a `PersistentVolumeClaim` (`tiktoken-cache-pvc`, 1Gi CephFS ReadWriteMany) is created alongside the Deployment. An init container downloads the files into the PVC on the **first** pod start only; because the PVC persists across restarts and rescheduling, subsequent init container runs find the files already cached and exit in under a second. The `ReadWriteMany` access mode means the PVC also works correctly if `replicas` is increased.

To apply changes on OpenShift after editing `config.yaml` / `deploy-litellm.yaml`:

```bash
oc apply -f deploy-litellm.yaml
oc rollout restart deployment/litellm-gw -n litellm-gw
oc rollout status deployment/litellm-gw -n litellm-gw
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Permission denied` mounting `config.yaml` | SELinux blocking rootless volume | Ensure `:ro,z` is on the `-v` flag in `run.sh` |
| `Connection refused` to local vLLM/Ollama | `localhost` resolves to container loopback | Use `host.containers.internal` in `.env` |
| Container exits after SSH logout | Systemd user session ended | `loginctl enable-linger $USER` |
| Pod `CrashLoopBackOff` on OpenShift | Bad key or unreachable provider at startup | `oc logs deploy/litellm-gw -n litellm-gw` |
| Startup very slow (>30 s) | Telemetry call + sequential model health probes + CDN tokenizer fetches | Ensure `telemetry: false`, `health_check_interval: 300` in `config.yaml`; run `download-tiktoken-cache.sh` |
| Readiness probe failing on slow start | `initialDelaySeconds` too short | Increase `initialDelaySeconds` on the readiness probe in `deploy-litellm.yaml` |
| Init container fails on OpenShift | CDN blocked or no egress to port 443 | Verify NetworkPolicy allows egress to `0.0.0.0/0:443`; check `oc logs pod/<pod> -c tiktoken-init` |
| Init container re-downloads on every restart | PVC not bound / using emptyDir | Check `oc get pvc tiktoken-cache-pvc -n litellm-gw`; PVC should be `Bound` |
| `401 Unauthorized` from client | Wrong or missing Bearer token | Use the value of `LITELLM_MASTER_KEY` from your secret |
| NetworkPolicy blocking egress | New provider added not covered by port 443 | Check provider port; add an egress rule for the new port |
| `ImagePullBackOff` | OCP can't reach ghcr.io | Add a pull secret or pre-pull the image to a mirror |
