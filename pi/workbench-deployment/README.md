# pi Workbench — OpenShift AI Deployment

Deploys the pi AI coding agent as an **OpenShift AI (RHOAI/ODH) Workbench** image, accessible from the browser via a ttyd web terminal.

## Architecture

```
[RHOAI Dashboard] → creates Workbench pod
                         │
             [nginx :8080]  ← port RHOAI requires
                    │
             [ttyd  :7681]  ← WebSocket terminal
                    │
              [pi CLI]      ← AI coding agent
                    │
           [PVC: .pi/agent] ← persistent sessions, settings, extensions
```

## Files

| File | Purpose |
|---|---|
| `imagestream.yaml` | Registers the image with RHOAI (apply in `redhat-ods-applications` ns) |
| `secret-api-keys.yaml` | LLM provider API keys — edit before applying |
| `pvc.yaml` | 2 Gi PVC for persistent pi state (if deploying standalone) |

---

## Option A — Use via RHOAI Dashboard (recommended)

RHOAI discovers workbench images through `ImageStream` objects in the `redhat-ods-applications` namespace.

### 1. Build and push the image

```bash
# From the repo root
podman build -t quay.io/<your-org>/pi-workbench:v1 -f Containerfile-workbench .
podman push quay.io/<your-org>/pi-workbench:v1
```

### 2. Register the image with RHOAI

Edit `imagestream.yaml` — replace `quay.io/<your-org>/pi-workbench:v1` with your registry path.

```bash
# Apply in the RHOAI operator namespace
oc apply -f workbench-deployment/imagestream.yaml
```

> For **ODH** (not RHOAI), change the namespace to `opendatahub` before applying.

RHOAI reconciles custom images within a few minutes. You will see **Pi Coding Agent** appear under **Settings → Notebook Images** in the RHOAI dashboard.

### 3. Create the Workbench

1. Open the RHOAI dashboard → your Data Science Project → **Workbenches → Create workbench**
2. Select **Pi Coding Agent** from the notebook image list
3. Under **Environment variables**, add the API key secret:
   - Click **Add secret** → select `pi-workbench-api-keys`
   - (Create the secret first: `oc apply -f workbench-deployment/secret-api-keys.yaml`)
4. Under **Cluster storage**, attach a PVC to `/opt/app-root/.pi/agent` (2 Gi recommended) for session persistence
5. Click **Create workbench** — RHOAI provisions the pod and injects `NB_PREFIX` automatically

### 4. Open the workbench

Click **Open** in the RHOAI dashboard. The browser will navigate to the pi terminal.

---

## Option B — Standalone deployment (without RHOAI)

For testing or clusters without RHOAI, deploy manually.  
The workbench image still listens on port 8080 and defaults `NB_PREFIX` to `/pi`.

```bash
oc project <your-namespace>

# API keys
oc apply -f workbench-deployment/secret-api-keys.yaml

# Persistent volume
oc apply -f workbench-deployment/pvc.yaml

# Deployment
oc create deployment pi-workbench \
  --image=quay.io/<your-org>/pi-workbench:v1 \
  --port=8080

oc set env deployment/pi-workbench --from=secret/pi-workbench-api-keys

oc set volume deployment/pi-workbench \
  --add --name=pi-agent-home \
  --type=persistentVolumeClaim \
  --claim-name=pi-workbench-agent-pvc \
  --mount-path=/opt/app-root/.pi/agent

# Expose
oc expose deployment/pi-workbench --port=8080 --name=pi-workbench
oc create route edge pi-workbench \
  --service=pi-workbench \
  --insecure-policy=Redirect
```

Access: open the route URL → it redirects to `/pi/`.

---

## Local test with Podman

```bash
# Create a named volume for persistence
podman volume create pi-workbench-agent

podman run --rm -p 8080:8080 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e NB_PREFIX=/pi \
  -v pi-workbench-agent:/opt/app-root/.pi/agent \
  quay.io/<your-org>/pi-workbench:v1
```

Open `http://localhost:8080/pi/` in a browser.

---

## Persistent Volume

What is stored in `/opt/app-root/.pi/agent` (the PVC mount):

| Path | Contents |
|---|---|
| `sessions/` | Conversation history (auto-saved per working directory) |
| `settings.json` | Global settings (model, theme, transport, thinking level) |
| `keybindings.json` | Custom keyboard shortcuts |
| `trust.json` | Project trust decisions |
| `AGENTS.md` | Global system prompt additions |
| `SYSTEM.md` | Custom system prompt override |
| `extensions/` | Installed extensions |
| `skills/` | Installed skills |
| `themes/` | Custom themes |
| `prompts/` | Prompt templates |
| `models.json` | Custom provider/model definitions |

---

## NB_PREFIX behaviour

| Variable | Behaviour |
|---|---|
| Not set | Defaults to `/pi` — terminal served at `http://host:8080/pi/` |
| Set by RHOAI | e.g. `/notebookserver/notebooks/default/my-pi` — nginx and ttyd both use this prefix automatically |

`run.sh` generates the nginx server config at pod startup via `envsubst`, so no image rebuild is needed when the prefix changes.

---

## Security notes

- Pod runs `runAsNonRoot: true` — OpenShift assigns an arbitrary UID from the namespace range; the image pre-creates directories owned `1001:0` with `g=u` so any UID in GID 0 can write.
- API keys are injected as environment variables from a Secret — never baked into the image.
- ttyd has no built-in authentication — RHOAI provides OAuth proxy authentication in front of the workbench automatically. For standalone deployments, add `--credential user:pass` to the `ttyd` command in `run.sh`.
