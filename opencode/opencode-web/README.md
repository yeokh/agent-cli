# opencode-web container

Runs [opencode](https://opencode.ai) in web-UI mode (`opencode web`) inside a
UBI 9 container image, suitable for both local podman use and OpenShift
deployment.

---

## Directory layout

```
opencode/opencode-web/
├── Containerfile          # Image build definition
├── entrypoint.sh          # Container startup script
├── podman-run.sh          # Local podman helper
└── deployment/
    ├── secret.yaml        # Auth credentials + LLM API keys (OpenShift Secret)
    ├── pvc.yaml           # PersistentVolumeClaims
    ├── deployment.yaml    # OpenShift / Kubernetes Deployment
    ├── service.yaml       # Service
    └── route.yaml         # OpenShift Route (TLS edge termination)
```

---

## Volume mount points

| Mount path | Type | Purpose |
|---|---|---|
| `/workspace` | rw | Project source files |
| `/home/opencode/.config/opencode` | rw | Persistent opencode config (`opencode.jsonc`) and plugins |
| `/home/opencode/.local/share/opencode` | rw | Sessions DB, auth tokens, snapshots |
| `/home/opencode/.opencode/agent` | **ro** | Agent instruction files (`AGENTS.md`, `.md`) |
| `/home/opencode/.cursor/skills-cursor` | **ro** | Cursor skill definitions |

---

## Build

```bash
podman build -t opencode-web:latest .
```

---

## Run locally with podman

The helper script creates named podman volumes (matching the PVC names in
`pvc.yaml`) and runs the container:

```bash
ANTHROPIC_API_KEY=sk-ant-... \
OPENCODE_SERVER_PASSWORD=mysecret \
./podman-run.sh
```

To also seed the read-only agent/skills volumes from local paths on first run:

```bash
SEED_AGENT_DIR=~/.opencode/agent \
SEED_SKILLS_DIR=~/.cursor/skills-cursor \
ANTHROPIC_API_KEY=sk-ant-... \
OPENCODE_SERVER_PASSWORD=mysecret \
./podman-run.sh
```

Open `http://localhost:8081` in your browser.

Volume names (inspect or remove with `podman volume ls / rm`):

| Podman volume | Maps to OpenShift PVC |
|---|---|
| `opencode-workspace` | `opencode-workspace-pvc` |
| `opencode-config` | `opencode-config-pvc` |
| `opencode-data` | `opencode-data-pvc` |
| `opencode-agent` | `opencode-agent-pvc` |
| `opencode-skills` | `opencode-skills-pvc` |

---

## Deploy to OpenShift

### 1. Edit the Secret

```bash
# Fill in real values before applying
vi deployment/secret.yaml
```

### 2. Apply all manifests

```bash
oc apply -f deployment/secret.yaml
oc apply -f deployment/pvc.yaml
oc apply -f deployment/service.yaml
oc apply -f deployment/route.yaml

oc apply -f deployment/deployment.yaml
```

### 3. Seed the read-only volumes

Agent instructions and skills are read-only PVCs. Populate them before (or
after) the first deployment by scaling down, running a temporary pod, copying
files, then scaling back up:

```bash
oc scale deployment opencode-web --replicas=0

oc run seed --image=registry.redhat.io/ubi9/nodejs-24-minimal --restart=Never \
  --overrides='{"spec":{"volumes":[{"name":"agent","persistentVolumeClaim":{"claimName":"opencode-agent-pvc"}}],"containers":[{"name":"seed","image":"registry.redhat.io/ubi9/nodejs-24-minimal","command":["sleep","3600"],"volumeMounts":[{"mountPath":"/agent","name":"agent"}]}]}}'
oc cp ~/.opencode/agent/. seed:/agent/
oc delete pod seed

oc scale deployment opencode-web --replicas=1
```

### 4. Get the URL

```bash
oc get route opencode-web -o jsonpath='{.spec.host}'
```

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `OPENCODE_SERVER_USERNAME` | `opencode` | Basic-auth username |
| `OPENCODE_SERVER_PASSWORD` | *(empty)* | Basic-auth password -- **set this** |
| `OPENCODE_PORT` | `8081` | Listening port |
| `OPENCODE_HOSTNAME` | `0.0.0.0` | Bind address |
| `OPENCODE_CORS` | *(empty)* | Additional CORS origin(s) |
| `OPENCODE_DISABLE_AUTOUPDATE` | `true` | Prevent in-container self-update |
| `ANTHROPIC_API_KEY` | *(empty)* | Anthropic API key |
| `OPENAI_API_KEY` | *(empty)* | OpenAI API key |
| `GOOGLE_AI_API_KEY` | *(empty)* | Google AI API key |
