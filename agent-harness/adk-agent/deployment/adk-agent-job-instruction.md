# ADK Agent — Headless Batch Jobs on OpenShift

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
podman build -t quay.io/khyeo/adk-agent:v1 -f Containerfile .
podman login quay.io
podman push quay.io/khyeo/adk-agent:v1
```

---

## Step 2 — Running a Single Batch Job (existing workflow)

This uses the static `adk-agent-job.yaml` with a fixed set of shared PVCs.
Suitable when you only need to run one job at a time.

### 2a. Create shared PVCs (first time only)

```bash
oc apply -f deployment/pvc.yaml
```

### 2b. Create or update ConfigMaps from local files

```bash
# Agent instruction
oc create configmap adk-agent-instruction \
  --from-file=agent/instruction.md \
  --dry-run=client -o yaml | oc apply -f -

# Input payload files
oc create configmap adk-agent-input-files \
  --from-file=input/ \
  --dry-run=client -o yaml | oc apply -f -
```

### 2c. Submit the job

```bash
oc apply -f deployment/adk-agent-job.yaml
```

### 2d. Re-running the job

Job names must be unique. Delete the completed job before re-running:

```bash
oc delete job adk-agent-job
oc apply -f deployment/adk-agent-job.yaml
```

---

## Step 3 — Running Multiple Jobs in Parallel (per-job template)

Each job gets its own input/output PVCs and ConfigMaps so jobs are fully
isolated and can run concurrently without contention.

### 3a. Set a unique job ID

```bash
JOB_ID=job-001   # change for each run, e.g. job-002, job-20260627, etc.
```

### 3b. Create per-job PVCs

```bash
sed "s/JOB_ID/$JOB_ID/g" deployment/adk-agent-job-pvc-template.yaml \
  | oc apply -f -
```

### 3c. Create per-job ConfigMaps

```bash
oc create configmap adk-$JOB_ID-instruction \
  --from-file=agent/instruction.md \
  --dry-run=client -o yaml | oc apply -f -

oc create configmap adk-$JOB_ID-input-files \
  --from-file=input/ \
  --dry-run=client -o yaml | oc apply -f -
```

### 3d. Submit the job

```bash
sed "s/JOB_ID/$JOB_ID/g" deployment/adk-agent-job-template.yaml \
  | oc apply -f -
```

Repeat steps 3a–3d with a different `JOB_ID` to run additional jobs in parallel.

---

## Step 4 — Monitor Jobs

```bash
# List all agent jobs and their status
oc get jobs -l app=adk-agent

# Watch a specific job
oc get job adk-$JOB_ID -w

# Follow logs by job ID label
oc logs -f -l job-id=$JOB_ID --max-log-requests=1

# Or by pod name
oc get pods -l job-id=$JOB_ID
oc logs -f <pod-name>
```

The initContainer (`seed-volumes`) runs first and copies instruction and input
files into the job volumes. Wait for the main `adk-agent` container to start
before expecting agent output in the logs.

Job completion states:
- `Complete` — agent finished successfully
- `Failed` — agent exited non-zero; check logs. Job retries once (`backoffLimit: 1`).

---

## Step 5 — Retrieve Output Files

Output is written to `adk-$JOB_ID-output-pvc`. Use a temporary reader pod to
copy files locally.

```bash
# Start a reader pod
oc run output-reader-$JOB_ID \
  --image=registry.access.redhat.com/ubi9/ubi9 \
  --restart=Never \
  --overrides="{
    \"spec\": {
      \"containers\": [{
        \"name\": \"reader\",
        \"image\": \"registry.access.redhat.com/ubi9/ubi9\",
        \"command\": [\"sleep\", \"3600\"],
        \"volumeMounts\": [{\"name\": \"out\", \"mountPath\": \"/app/output\"}]
      }],
      \"volumes\": [{\"name\": \"out\", \"persistentVolumeClaim\": {\"claimName\": \"adk-$JOB_ID-output-pvc\"}}]
    }
  }"

# Wait for it to be ready
oc wait pod/output-reader-$JOB_ID --for=condition=Ready --timeout=60s

# Copy output files to local directory
oc cp output-reader-$JOB_ID:/app/output ./output-$JOB_ID/

# Clean up the reader pod
oc delete pod output-reader-$JOB_ID
```

---

## Step 6 — Clean Up a Completed Job

After retrieving output, remove all per-job resources to free up storage:

```bash
oc delete job adk-$JOB_ID
oc delete pvc adk-$JOB_ID-input-pvc adk-$JOB_ID-output-pvc
oc delete configmap adk-$JOB_ID-instruction adk-$JOB_ID-input-files
```

> **Note:** Jobs with `ttlSecondsAfterFinished: 600` are auto-deleted by
> Kubernetes 10 minutes after completion, but the PVCs and ConfigMaps must
> always be deleted manually.

---

## Deployment Files Reference

| File | Purpose |
|------|---------|
| `Containerfile` | Unified image (web + headless, controlled by `RUN_MODE`) |
| `entrypoint.sh` | Image entrypoint — routes to `web_app.py` or `adk_agent.py` |
| `pvc.yaml` | Shared PVCs for the single-job workflow |
| `adk-agent-job.yaml` | Static single-job definition (shared PVCs) |
| `adk-agent-job-template.yaml` | Per-job template for parallel runs |
| `adk-agent-job-pvc-template.yaml` | Per-job PVC template (input + output) |
| `deployment.yaml` | Web UI deployment (`RUN_MODE=web`) |
| `service.yaml` | ClusterIP service for the web UI |
| `route.yaml` | OpenShift route to expose the web UI |
| `secret-api-keys.yaml` | API key secret (edit before applying) |

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `RUN_MODE` | `agent` | `agent` = headless batch, `web` = Flask web UI |
| `API_PROVIDER` | `anthropic` | LLM provider: `anthropic`, `openrouter`, `openai-compatible` |
| `MODEL` | `claude-haiku-4-5` | Model name passed to the provider |
| `MAX_TURNS` | `50` | Maximum agent turns before forced stop |
| `ALLOW_SHELL` | `true` | Whether the agent can execute shell commands |
| `SHELL_TIMEOUT` | `60` | Timeout in seconds for each shell command |
| `AGENT_DIR` | `/app/agent` | Directory containing `instruction.md` |
| `INPUT_DIR` | `/app/input` | Directory containing payload files |
| `OUTPUT_DIR` | `/app/output` | Directory where output files are written |
| `PORT` | `8080` | Web UI bind port (web mode only) |
| `HOST` | `0.0.0.0` | Web UI bind host (web mode only) |

API keys are supplied via the `adk-agent-api-keys` secret, not as plain env vars.
