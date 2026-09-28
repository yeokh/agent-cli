# nanobot — Hardened Container Deployment

Builds and deploys [nanobot](https://github.com/HKUDS/nanobot) using
Project Hummingbird hardened base images and Red Hat UBI9 Minimal runtime.
Supports local `podman run`, a standalone ttyd web terminal, and OpenShift Dev Spaces.

## Image overview

| File | Base images | Purpose |
|---|---|---|
| `Containerfile` | Hummingbird nodejs/python builders → ubi9-minimal | Standalone hardened image (Render, podman, OpenShift) |
| `Containerfile-ttyd` | ubi9 + uv (PyPI install) | Browser-accessible web terminal via ttyd (OpenShift Route) |
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

Commands for `Containerfile` and `Containerfile-devspaces` run from the
**nanobot repo root** (the directory containing `pyproject.toml`, `webui/`, etc.).
`Containerfile-ttyd` is built from the `deployment/` directory as its context.

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

### ttyd web terminal image

Installs nanobot-ai from PyPI — no source build required.
Context is the `deployment/` directory (not the repo root).

```bash
podman build \
  -t quay.io/<your-org>/nanobot-ttyd:v1 \
  -f deployment/Containerfile-ttyd \
  deployment/

podman push quay.io/<your-org>/nanobot-ttyd:v1
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
NANOBOT_AGENTS__DEFAULTS__PROVIDER=anthropic
NANOBOT_AGENTS__DEFAULTS__MODEL=anthropic/claude-opus-4-5
EOF
chmod 600 ~/.nanobot.env
```

> **Provider env vars** — nanobot reads the standard SDK keys directly:
> `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, etc.
> Use `NANOBOT_AGENTS__DEFAULTS__PROVIDER` and `NANOBOT_AGENTS__DEFAULTS__MODEL`
> to pin which provider and model nanobot uses.

All `podman run` examples below use `--env-file ~/.nanobot.env`.

---

podman run -it --rm -p 7681:7681 -v nanobot-data:/home/nanobot/.nanobot \
  quay.io/kenghua_yeo/nanobot-ttyd:v1 /bin/bash

podman run -it --rm -p 7681:7681 -v nanobot-data:/home/nanobot/.nanobot \
  --entrypoint /bin/bash quay.io/kenghua_yeo/nanobot-ttyd:v1


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

Replace `status` with any nanobot subcommand (`channels list`, `agent`, `webui --no-open --yes`, etc.).

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

### ttyd web terminal (local)

The `nanobot-ttyd` image exposes a browser-accessible terminal via
[ttyd](https://github.com/tsl0922/ttyd) on port **7681**.
The terminal command is controlled by the `NANOBOT_TTYD_CMD` env var.

```bash
podman run --rm -p 7681:7681 \
  -e ANTHROPIC_API_KEY=<your-key> \
  -v nanobot-data:/home/nanobot/.nanobot \
  quay.io/<your-org>/nanobot-ttyd:v1
```

Open **http://localhost:7681** in your browser.

Optional flags:

```bash
# Plain bash shell instead of the nanobot agent
-e NANOBOT_TTYD_CMD=bash

# Gateway + WebUI mode (also expose those ports)
-e NANOBOT_TTYD_CMD=webui -p 18790:18790 -p 8765:8765

# Persist workspace files too
-v nanobot-workspace:/home/nanobot/workspace
```

---

## Deploy on OpenShift

Three deployment modes are available.  All are compatible with the `restricted-v2`
SCC (no root, no privilege escalation, arbitrary UID supported).

---

### Mode 1 — Standalone gateway + WebUI

Uses the hardened multi-stage image (`Containerfile`) built from the nanobot repo root.

#### 1. Build and push

```bash
podman build -t quay.io/<your-org>/nanobot:latest \
  -f deployment/Containerfile .
podman push quay.io/<your-org>/nanobot:latest
```

Update `deployment/deployment.yaml` with your image reference.

#### 2. Create the Secret

```bash
oc create secret generic nanobot-api-keys \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-... \
  --from-literal=NANOBOT_AGENTS__DEFAULTS__PROVIDER=anthropic \
  --from-literal=NANOBOT_AGENTS__DEFAULTS__MODEL=anthropic/claude-opus-4-5
```

#### 3. Apply manifests

```bash
oc apply -f deployment/pvc.yaml
oc apply -f deployment/deployment.yaml
oc apply -f deployment/service.yaml
oc apply -f deployment/route.yaml
```

```bash
oc rollout status deployment/nanobot
oc get routes
```

---

### Mode 2 — ttyd web terminal

Exposes nanobot (or a plain shell) as a browser-accessible terminal via
[ttyd](https://github.com/tsl0922/ttyd).  Uses the single-stage image
(`Containerfile-ttyd`) built from the `deployment/` directory.

The **terminal command** is controlled by the `NANOBOT_TTYD_CMD` env var:

| Value | What ttyd serves |
|---|---|
| `agent` (default) | `nanobot agent` — interactive TUI agent session |
| `webui` | `nanobot webui --no-open --yes` — gateway + WebUI server (headless) |
| `bash` | plain bash shell with nanobot on PATH |

#### 1. Build and push

```bash
podman build \
  -t quay.io/<your-org>/nanobot-ttyd:v1 \
  -f deployment/Containerfile-ttyd \
  deployment/
podman push quay.io/<your-org>/nanobot-ttyd:v1
```

Update `deployment/ttyd-deployment.yaml` with your image reference.

#### 2. Create the Secret

```bash
# Anthropic example
oc create secret generic nanobot-ttyd-api-keys \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-... \
  --from-literal=NANOBOT_AGENTS__DEFAULTS__PROVIDER=anthropic \
  --from-literal=NANOBOT_AGENTS__DEFAULTS__MODEL=anthropic/claude-opus-4-5

# OpenAI example
oc create secret generic nanobot-ttyd-api-keys \
  --from-literal=OPENAI_API_KEY=sk-proj-... \
  --from-literal=NANOBOT_AGENTS__DEFAULTS__PROVIDER=openai \
  --from-literal=NANOBOT_AGENTS__DEFAULTS__MODEL=openai/gpt-4o

# Google Gemini example
oc create secret generic nanobot-ttyd-api-keys \
  --from-literal=GEMINI_API_KEY=AIza... \
  --from-literal=NANOBOT_AGENTS__DEFAULTS__PROVIDER=gemini \
  --from-literal=NANOBOT_AGENTS__DEFAULTS__MODEL=gemini/gemini-2.0-flash
```

#### 3. Apply manifests

```bash
oc apply -f deployment/ttyd-pvc.yaml
oc apply -f deployment/ttyd-deployment.yaml
oc apply -f deployment/ttyd-service.yaml
oc apply -f deployment/ttyd-route.yaml
```

```bash
oc rollout status deployment/nanobot-ttyd
oc get routes nanobot-ttyd
```

Open the Route URL in a browser — you get a full nanobot terminal session.

> **webui mode note:** when `NANOBOT_TTYD_CMD=webui`, nanobot starts its gateway
> (port 18790) and WebUI server (port 8765) inside the terminal session.  To access
> those services directly, add additional Services and Routes for those ports.

---

### Mode 3 — Dev Spaces

Uses the UDI-based image (`Containerfile-devspaces`) built from the nanobot repo root.
DevSpaces auto-creates HTTPS routes for the exposed ports.

#### 1. Build and push the Dev Spaces image

```bash
podman build \
  -t quay.io/<your-org>/nanobot-devspaces:latest \
  -f deployment/Containerfile-devspaces .
podman push quay.io/<your-org>/nanobot-devspaces:latest
```

#### 2. Update `devfile.yaml`

Replace `quay.io/<your-org>/nanobot-devspaces:latest` with your image reference.

#### 3. Create the Secret in the Dev Spaces namespace

```bash
oc create secret generic nanobot-api-keys \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-... \
  --from-literal=NANOBOT_AGENTS__DEFAULTS__PROVIDER=anthropic \
  --from-literal=NANOBOT_AGENTS__DEFAULTS__MODEL=anthropic/claude-opus-4-5
```

Uncomment the `secretKeyRef` env blocks in `devfile.yaml`.

#### 4. Open the workspace

Via the Dev Spaces dashboard, or:

```
https://<devspaces-host>/dashboard/#/load-factory?url=<repo-url>
```

DevSpaces auto-creates HTTPS routes for:
- Port **18790** → `nanobot-gateway` (health endpoint)
- Port **8765** → `nanobot-webui` (browser workbench)

Default devfile commands (run from the DevSpaces terminal or Commands palette):

| Label | Command |
|---|---|
| `1. Start nanobot WebUI` | `nanobot webui --no-open --yes` |
| `2. Start nanobot agent` | `nanobot agent` |
| `3. nanobot status` | `nanobot status` |
| `4. List nanobot channels` | `nanobot channels list` |

---

### OpenShift SCC note

All three deployment modes run with `runAsNonRoot: true` and
`allowPrivilegeEscalation: false`, compatible with the `restricted-v2` SCC.
OpenShift injects an arbitrary UID from the project's range; the images use
`chown <uid>:0 + g+rwX` on data directories so that arbitrary UID can write
without needing root.

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
