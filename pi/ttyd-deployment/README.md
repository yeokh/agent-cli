# pi-ttyd — OpenShift Deployment

Web terminal interface for the [pi](https://github.com/earendil-works/pi) AI coding agent CLI, served via [ttyd](https://github.com/tsl0922/ttyd).  
Access pi from any browser without installing anything locally.

## Architecture

```
Browser → OpenShift Route (TLS) → Service :7681 → Pod (ttyd → pi)
                                                         │
                                              PVC: pi-agent-home
                                              /opt/app-root/.pi/agent
```

## Files

| File | Purpose |
|---|---|
| `secret-api-keys.yaml` | LLM provider API keys (edit before applying) |
| `pvc.yaml` | 2 Gi PVC for persistent pi state |
| `deployment.yaml` | Deployment — 1 replica, non-root, resource limits |
| `service.yaml` | ClusterIP Service on port 7681 |
| `route.yaml` | Edge-terminated HTTPS Route |

---

## Prerequisites

- `podman` or `docker` to build the image
- Access to a container registry (e.g. `quay.io`)
- `oc` CLI logged in to your OpenShift cluster
- An OpenShift project/namespace to deploy into

---

## 1. Build and Push the Image

```bash
# From the repo root (where Containerfile-ttyd lives)
podman build -t quay.io/<your-org>/pi-ttyd:v1 -f Containerfile-ttyd .
podman push quay.io/<your-org>/pi-ttyd:v1
```

Update the `image:` field in `deployment.yaml` to match your registry path.

---

## 2. Configure API Keys

Edit `secret-api-keys.yaml` and fill in at least one provider key:

```yaml
stringData:
  ANTHROPIC_API_KEY: "sk-ant-..."
  OPENAI_API_KEY: "sk-..."
  OPENROUTER_API_KEY: "sk-or-..."
  GEMINI_API_KEY: "AI..."
```

Remove keys for providers you are not using. Do **not** commit this file with real keys.

---

## 3. Deploy to OpenShift

Apply all resources in order:

```bash
# Select your project
oc project <your-namespace>

# API keys
oc apply -f deployment/secret-api-keys.yaml

# Persistent volume (pi sessions, settings, extensions)
oc apply -f deployment/pvc.yaml

# Deployment, Service, Route
oc apply -f deployment/deployment.yaml
oc apply -f deployment/service.yaml
oc apply -f deployment/route.yaml
```

Or apply everything at once:

```bash
oc apply -f deployment/
```

Check rollout status:

```bash
oc rollout status deployment/pi-ttyd
oc get route pi-ttyd
```

Open the URL shown by `oc get route pi-ttyd` in a browser to access the pi terminal.

---

## 4. Persistent Volume

The PVC `pi-ttyd-agent-pvc` is mounted at `/opt/app-root/.pi/agent` inside the container.  
Everything pi saves there persists across pod restarts and re-deployments:

| Path (inside volume) | Contents |
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
| `git/`, `npm/` | Installed pi packages |
| `models.json` | Custom provider/model definitions |

---

## 5. Local Run with Podman

### Create a named volume

```bash
podman volume create pi-agent-home
```

### Run with the volume

```bash
podman run --rm -it \
  -p 7681:7681 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -v pi-agent-home:/opt/app-root/.pi/agent \
  quay.io/<your-org>/pi-ttyd:v1
```

# You can also run with /bin/bash and then export API key within the container.

Open `http://localhost:7681` in a browser.

### Inspect or back up the volume

```bash
# Inspect volume location on host
podman volume inspect pi-agent-home

# Back up
podman run --rm \
  -v pi-agent-home:/data \
  -v "$PWD:/backup" \
  ubi9/ubi tar czf /backup/pi-agent-home.tar.gz -C /data .

# Restore
podman run --rm \
  -v pi-agent-home:/data \
  -v "$PWD:/backup" \
  ubi9/ubi tar xzf /backup/pi-agent-home.tar.gz -C /data
```

---

## 6. Teardown

```bash
oc delete -f deployment/
```

The PVC is **not** deleted by the above command — volume data is retained.  
To also delete the volume:

```bash
oc delete pvc pi-ttyd-agent-pvc
```

---

## Security Notes

- The pod runs with `runAsNonRoot: true` and no hardcoded UID/GID — OpenShift assigns a UID from the namespace's allowed range and a GID of 0. The image pre-creates `/opt/app-root/.pi/agent` owned by `xxx:0` with group-write (`chmod g=u`), so any arbitrary UID running in GID 0 (OpenShift's default) can write to the volume. Compatible with the `restricted-v2` and `restricted-v3` SCCs.
- ttyd has **no authentication** by default. The Route uses TLS edge termination but the terminal itself is open to anyone who can reach the URL.  
  Options to restrict access:
  - Add `--credential user:password` to the `CMD` in `Containerfile-ttyd` for HTTP basic auth.
  - Deploy an OAuth proxy sidecar and update the Route to point at it.
  - Use an OpenShift NetworkPolicy to restrict which namespaces/pods can reach the Service.
- API keys are stored in an Opaque Secret and injected as environment variables — not baked into the image.
