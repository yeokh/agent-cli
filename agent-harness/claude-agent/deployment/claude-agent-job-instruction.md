# Claude Agent — Headless Batch Jobs on OpenShift

This guide covers building the unified agent image, running one-off batch jobs,
and running multiple jobs in parallel using per-job templates.

---

## Prerequisites

- OpenShift CLI (`oc`) installed and logged in
- Active project set: `oc project <your-namespace>`
- API keys secret already created: `oc apply -f deployment/secret-api-keys.yaml`
  _(edit the secret file first to fill in your real API key values)_

---

## Step 1 — Build and Push the Image

A single image supports both headless batch (`RUN_MODE=agent`) and web UI
(`RUN_MODE=web`) modes, controlled entirely by an environment variable.

```bash
podman build -t quay.io/khyeo/claude-agent:v1 -f Containerfile .
podman login quay.io
podman push quay.io/khyeo/claude-agent:v1
```

---

## Step 2 — Running a Single Batch Job

### 2a. Create shared PVCs (first time only)

```bash
oc apply -f deployment/pvc.yaml
```

### 2b. Create or update ConfigMaps from local files

```bash
# Agent instruction
oc create configmap claude-agent-instruction \
  --from-file=agent/instruction.md \
  --dry-run=client -o yaml | oc apply -f -

# Input payload files
oc create configmap claude-agent-input-files \
  --from-file=input/ \
  --dry-run=client -o yaml | oc apply -f -
```

### 2c. Submit the job

```bash
JOB_ID=job-001
sed "s/JOB_ID/$JOB_ID/g" deployment/claude-agent-job-template.yaml \
  | oc apply -f -
```

---

## Step 3 — Running Multiple Jobs in Parallel

Each job gets its own input/output PVCs and ConfigMaps so jobs are fully
isolated and can run concurrently without contention.

### 3a. Set a unique job ID

```bash
JOB_ID=job-001   # change for each run
```

### 3b. Create per-job PVCs

```bash
sed "s/JOB_ID/$JOB_ID/g" deployment/claude-agent-job-pvc-template.yaml \
  | oc apply -f -
```

### 3c. Create per-job ConfigMaps

```bash
oc create configmap claude-$JOB_ID-instruction \
  --from-file=agent/instruction.md \
  --dry-run=client -o yaml | oc apply -f -

oc create configmap claude-$JOB_ID-input-files \
  --from-file=input/ \
  --dry-run=client -o yaml | oc apply -f -
```

### 3d. Submit the job

```bash
sed "s/JOB_ID/$JOB_ID/g" deployment/claude-agent-job-template.yaml \
  | oc apply -f -
```

Repeat steps 3a–3d with a different `JOB_ID` to run additional jobs in parallel.

---

## Step 4 — Monitor Jobs

```bash
oc get jobs -l app=claude-agent
oc logs -f -l job-id=$JOB_ID --max-log-requests=1
```

---

## Step 5 — Retrieve Output Files

```bash
oc run output-reader-$JOB_ID \
  --image=registry.access.redhat.com/ubi9/ubi9 \
  --restart=Never \
  --overrides="{\"spec\":{\"containers\":[{\"name\":\"r\",\"image\":\"registry.access.redhat.com/ubi9/ubi9\",\"command\":[\"sleep\",\"3600\"],\"volumeMounts\":[{\"name\":\"out\",\"mountPath\":\"/app/output\"}]}],\"volumes\":[{\"name\":\"out\",\"persistentVolumeClaim\":{\"claimName\":\"claude-$JOB_ID-output-pvc\"}}]}}"
oc wait pod/output-reader-$JOB_ID --for=condition=Ready --timeout=60s
oc cp output-reader-$JOB_ID:/app/output ./output-$JOB_ID/
oc delete pod output-reader-$JOB_ID
```

---

## Step 6 — Clean Up

```bash
oc delete job claude-$JOB_ID
oc delete pvc claude-$JOB_ID-input-pvc claude-$JOB_ID-output-pvc
oc delete configmap claude-$JOB_ID-instruction claude-$JOB_ID-input-files
```

---

## Deployment Files Reference

| File | Purpose |
|------|---------|
| `Containerfile` | Unified image (web + headless, controlled by `RUN_MODE`) |
| `entrypoint.sh` | Routes to `web_app.py` or `claude_agent.py` |
| `pvc.yaml` | Shared PVCs for the web UI deployment |
| `deployment.yaml` | Web UI deployment (`RUN_MODE=web`) |
| `service.yaml` | ClusterIP service for the web UI |
| `route.yaml` | OpenShift route to expose the web UI |
| `secret-api-keys.yaml` | API key secret (edit before applying) |
| `claude-agent-job-template.yaml` | Per-job template for batch runs |
| `claude-agent-job-pvc-template.yaml` | Per-job PVC template (input + output) |

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `RUN_MODE` | `agent` | `agent` = headless batch, `web` = Flask web UI |
| `API_PROVIDER` | `anthropic` | LLM provider: `anthropic`, `openrouter`, `openai-compatible` |
| `MODEL` | `claude-opus-4-5` | Model name passed to the provider |
| `MAX_TURNS` | `50` | Maximum agent turns before forced stop |
| `MAX_OUTPUT_TOKENS` | `16384` | Maximum tokens per model response |
| `ALLOW_SHELL` | `true` | Whether the agent can execute shell commands |
| `SHELL_TIMEOUT` | `60` | Timeout in seconds for each shell command |
| `AGENT_DIR` | `/app/agent` | Directory containing `instruction.md` |
| `INPUT_DIR` | `/app/input` | Directory containing payload files |
| `OUTPUT_DIR` | `/app/output` | Directory where output files are written |
| `PORT` | `8080` | Web UI bind port (web mode only) |
| `HOST` | `0.0.0.0` | Web UI bind host (web mode only) |

API keys are supplied via the `claude-agent-api-keys` secret, not as plain env vars.
