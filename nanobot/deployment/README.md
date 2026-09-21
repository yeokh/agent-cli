# nanobot — Hardened Container Deployment

Builds and deploys [nanobot](https://github.com/HKUDS/nanobot) using
Project Hummingbird hardened base images and Red Hat UBI9 Minimal runtime.
Supports local `podman run` and OpenShift Dev Spaces.

## Image overview

| File | Base images | Purpose |
|---|---|---|
| `Containerfile` | Hummingbird nodejs/python builders → ubi9-minimal | Standalone hardened image (Render, podman) |
| `Containerfile-devspaces` | Same builders → UDI ubi9 | Dev Spaces workspace editor image |

### Why these bases?

| Upstream | Hardened replacement |
|---|---|
| `node:24-bookworm-slim` | `quay.io/hummingbird/nodejs:24-builder` |
| `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` | `uv` binary copied from `ghcr.io/astral-sh/uv:latest` into `quay.io/hummingbird/python:3.12-builder` |
| Final Debian runtime | `registry.access.redhat.com/ubi9/ubi-minimal` |

Package renames from apt → dnf/microdnf:

| apt | dnf/microdnf |
|---|---|
| `openssh-client` | `openssh-clients` |
| `libmagic1` | `file-libs` |
| `ca-certificates`, `git`, `bubblewrap` | same names |

---

## Prerequisites

```bash
podman --version   # >= 4.x
```

---

## Build

All commands run from the **nanobot repo root** (the directory containing
`pyproject.toml`, `webui/`, `nanobot/`, etc.).

### Standalone image

```bash
podman build -t nanobot:latest -f deployment/Containerfile .
```

Optional build args:

```bash
# Include optional extras (e.g. slack, discord)
podman build -t nanobot:latest -f deployment/Containerfile \
  --build-arg NANOBOT_EXTRAS=slack,discord .

# Pre-install additional channels
podman build -t nanobot:latest -f deployment/Containerfile \
  --build-arg NANOBOT_CHANNELS=whatsapp,slack .
```

### Dev Spaces image

```bash
podman build \
  -t quay.io/<your-org>/nanobot-devspaces:latest \
  -f deployment/Containerfile-devspaces .

podman push quay.io/<your-org>/nanobot-devspaces:latest
```

---

## Run with podman

The upstream [`docker-compose.yml`](https://github.com/HKUDS/nanobot/blob/main/docker-compose.yml)
defines three services.  The equivalent `podman run` commands are below.

> **SELinux note (RHEL / Fedora / OpenShift):** the `:Z` suffix on `-v` mounts
> tells podman to relabel the host directory so the container can read/write it.
> Omit `:Z` on non-SELinux hosts (macOS, plain Ubuntu, WSL2).

### Common environment file (recommended)

Create `~/.nanobot.env` once so you don't repeat credentials on every run:

```bash
cat > ~/.nanobot.env <<'EOF'
ANTHROPIC_API_KEY=sk-ant-...
NANOBOT_WEB_TOKEN=<your-token>
EOF
chmod 600 ~/.nanobot.env
```

All `podman run` examples below use `--env-file ~/.nanobot.env`.

---

### Service 1 — Gateway (WebUI + WebSocket)

Equivalent to `docker-compose up nanobot-gateway`.

```bash
mkdir -p ~/.nanobot

podman run -d \
  --name nanobot-gateway \
  --env-file ~/.nanobot.env \
  --cap-drop ALL \
  --cap-add CHOWN,SETGID,SETUID \
  --security-opt no-new-privileges \
  -v ~/.nanobot:/home/nanobot/.nanobot:Z \
  -p 127.0.0.1:18790:18790 \
  -p 8765:8765 \
  --memory 1g --cpus 1 \
  --restart unless-stopped \
  nanobot:latest \
  gateway
```

| Endpoint | URL |
|---|---|
| Gateway health | http://localhost:18790/health |
| WebUI / WebSocket | http://localhost:8765 |

---

### Service 2 — API server

Equivalent to `docker-compose up nanobot-api`.

```bash
podman run -d \
  --name nanobot-api \
  --env-file ~/.nanobot.env \
  --cap-drop ALL \
  --cap-add CHOWN,SETGID,SETUID \
  --security-opt no-new-privileges \
  -v ~/.nanobot:/home/nanobot/.nanobot:Z \
  -p 127.0.0.1:8900:8900 \
  --memory 1g --cpus 1 \
  --restart unless-stopped \
  nanobot:latest \
  serve --host 0.0.0.0 -w /home/nanobot/.nanobot/api-workspace
```

API endpoint: http://localhost:8900

---

### Service 3 — CLI (interactive, one-shot)

Equivalent to `docker-compose run --rm nanobot-cli <command>`.

```bash
podman run --rm -it \
  --name nanobot-cli \
  --env-file ~/.nanobot.env \
  --cap-drop ALL \
  --cap-add CHOWN,SETGID,SETUID \
  --security-opt no-new-privileges \
  -v ~/.nanobot:/home/nanobot/.nanobot:Z \
  nanobot:latest \
  status
```

Replace `status` with any nanobot subcommand (`channel list`, `configure`, etc.).

---

### Running all services together

```bash
# Start gateway + API in the background
mkdir -p ~/.nanobot
podman run -d --name nanobot-gateway --env-file ~/.nanobot.env \
  --cap-drop ALL --cap-add CHOWN,SETGID,SETUID \
  --security-opt no-new-privileges \
  -v ~/.nanobot:/home/nanobot/.nanobot:Z \
  -p 127.0.0.1:18790:18790 -p 8765:8765 \
  --memory 1g --cpus 1 --restart unless-stopped \
  nanobot:latest gateway

podman run -d --name nanobot-api --env-file ~/.nanobot.env \
  --cap-drop ALL --cap-add CHOWN,SETGID,SETUID \
  --security-opt no-new-privileges \
  -v ~/.nanobot:/home/nanobot/.nanobot:Z \
  -p 127.0.0.1:8900:8900 \
  --memory 1g --cpus 1 --restart unless-stopped \
  nanobot:latest serve --host 0.0.0.0 -w /home/nanobot/.nanobot/api-workspace

# Check status
podman ps --filter name=nanobot
podman logs nanobot-gateway
podman logs nanobot-api
```

### Stop and clean up

```bash
podman stop nanobot-gateway nanobot-api
podman rm   nanobot-gateway nanobot-api
```

---

## Deploy on OpenShift

### 1. Build and push the image

```bash
podman build -t quay.io/<your-org>/nanobot:latest \
  -f deployment/Containerfile .
podman push quay.io/<your-org>/nanobot:latest
```

Update `deployment/openshift/deployment.yaml` with your image reference.

### 2. Create the API key Secret

```bash
oc create secret generic nanobot-api-keys \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-... \
  --from-literal=NANOBOT_WEB_TOKEN=<your-token>
```

### 3. Apply manifests

```bash
oc apply -f deployment/openshift/pvc.yaml
oc apply -f deployment/openshift/deployment.yaml
oc apply -f deployment/openshift/service.yaml
oc apply -f deployment/openshift/route.yaml
```

Check rollout:

```bash
oc rollout status deployment/nanobot
oc get routes
```

### OpenShift SCC note

The deployment runs with `runAsNonRoot: true` and `allowPrivilegeEscalation: false`
(compatible with `restricted-v2` SCC). OpenShift injects an arbitrary UID from the
project's range; `entrypoint.sh` detects a non-root UID and skips the
`chown`/`setpriv` path. The image's `chown nanobot:0 + g+rwX` on `/home/nanobot`
ensures the arbitrary UID can still write the data directory.

---

## Deploy in Dev Spaces

### 1. Build and push the Dev Spaces image

```bash
podman build \
  -t quay.io/<your-org>/nanobot-devspaces:latest \
  -f deployment/Containerfile-devspaces .
podman push quay.io/<your-org>/nanobot-devspaces:latest
```

### 2. Update `devfile.yaml`

Replace `quay.io/<your-org>/nanobot-devspaces:latest` with your image reference.

### 3. Create the API key Secret in the Dev Spaces namespace

```bash
oc create secret generic nanobot-api-keys \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-... \
  --from-literal=NANOBOT_WEB_TOKEN=<your-token>
```

Uncomment the `secretKeyRef` env blocks in `devfile.yaml`.

### 4. Open the workspace

Via the Dev Spaces dashboard, or:

```
https://<devspaces-host>/dashboard/#/load-factory?url=<repo-url>
```

The devfile exposes:
- Port **18790** → `nanobot-gateway` (HTTPS route, auto-created by DevSpaces)
- Port **8765** → `nanobot-webui` (HTTPS route, auto-created by DevSpaces)

---

## Troubleshooting

### bubblewrap not found during build

`bubblewrap` is in the UBI9 AppStream repo. If `microdnf install bubblewrap`
fails, enable the CRB repo:

```dockerfile
RUN microdnf install -y dnf-plugins-core \
    && dnf config-manager --set-enabled crb \
    && microdnf install -y bubblewrap
```

### Python venv path issues after copy to ubi9-minimal

The venv's `python3` symlink points to `/usr/bin/python3.12`. The final stage
installs `python3.12` via `microdnf` which places it at the same path. If you
see "python3.12: not found", confirm `python3.12` is available:

```bash
podman run --rm nanobot:latest python3.12 --version
```

### nanobot refuses to start on OpenShift ("started as root ... refusing to run as root")

This means the container is running as root (UID 0). Verify the deployment's
`securityContext.runAsNonRoot: true` is set and the namespace SCC enforces it.
The `restricted-v2` SCC enforced by default on modern OpenShift clusters prevents
root and ensures `id -u` returns the arbitrary non-root UID.
