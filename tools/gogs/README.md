# Gogs Self-hosted Git Server

A single-container self-hosted Git server built on [Gogs](https://gogs.io), designed for:

- **Disconnected / air-gapped environments** — all assets bundled in the pre-built binary
- **OpenShift DevSpaces** — runs under restricted-v2 SCC with an arbitrary injected UID
- **Standalone use** — works with plain `podman run`
- **Zero external dependencies** — SQLite database, built-in SSH server, no extra services

---

## Quick Start

### Build

```bash
# Standard build — downloads gogs binary from GitHub Releases during build:
podman build -t gogs-server:latest .

# Pin a specific version:
podman build --build-arg GOGS_VERSION=0.14.3 -t gogs-server:latest .
```

### Disconnected / Air-gapped Build

Download the release tarball on a connected machine:

```bash
curl -fsSL https://github.com/gogs/gogs/releases/download/v0.14.3/gogs_v0.14.3_linux_amd64.tar.gz \
     -o gogs.tar.gz
```

In `Containerfile`, uncomment the `COPY gogs.tar.gz` line (Option B) and comment out the `curl` block, then build:

```bash
podman build -t gogs-server:latest .
```

### Run Standalone

```bash
# Wizard mode — visit http://localhost:3000 on first run to configure:
podman run --rm -p 3000:3000 -p 2222:2222 \
  -v gogs-data:/data \
  gogs-server:latest

# Auto mode — admin account provisioned automatically on first start:
podman run --rm -p 3000:3000 -p 2222:2222 \
  -e GOGS_ADMIN_USER=admin \
  -e GOGS_ADMIN_PASSWORD=changeme \
  -e GOGS_ADMIN_EMAIL=admin@example.com \
  -v gogs-data:/data \
  gogs-server:latest
```

### Clone a repository

```bash
# HTTP:
git clone http://localhost:3000/<user>/<repo>.git

# SSH (built-in SSH server — no system sshd required):
git clone ssh://git@localhost:2222/<user>/<repo>.git
```

---

## First-run Modes

### Auto mode (recommended for automation)

Set `GOGS_ADMIN_PASSWORD` to a non-empty value. The entrypoint will:

1. Write `app.ini` with `INSTALL_LOCK=true` and SQLite defaults.
2. Create the admin account via `gogs admin user create`.
3. Start the web server — no wizard shown.

### Wizard mode (default)

Leave `GOGS_ADMIN_PASSWORD` empty. On first visit, the Gogs web installer is shown
with server and database settings pre-filled from environment variables. You only need
to supply admin credentials in the form.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GOGS_HTTP_PORT` | `3000` | HTTP listen port |
| `GOGS_SSH_PORT` | `2222` | Built-in SSH server port |
| `GOGS_DOMAIN` | `localhost` | External hostname used in clone URLs |
| `GOGS_ADMIN_USER` | `gogs` | Initial admin username |
| `GOGS_ADMIN_PASSWORD` | `""` | Initial admin password (empty = wizard mode) |
| `GOGS_ADMIN_EMAIL` | `gogs@localhost` | Initial admin e-mail |
| `GOGS_CUSTOM` | `/data/gogs` | Custom config/data root (`app.ini` lives here) |

---

## OpenShift Deployment

### Create resources

```bash
# Create namespace (if needed):
oc new-project gogs

# Apply manifests:
oc apply -f deployment/pvc.yaml
oc apply -f deployment/secret.yaml
oc apply -f deployment/deployment.yaml
oc apply -f deployment/service.yaml
oc apply -f deployment/route.yaml
```

### Set admin password via Secret

```bash
oc create secret generic gogs-secret \
  --from-literal=GOGS_ADMIN_USER=admin \
  --from-literal=GOGS_ADMIN_PASSWORD=changeme \
  --from-literal=GOGS_ADMIN_EMAIL=admin@example.com \
  --dry-run=client -o yaml | oc apply -f -
```

### Update GOGS_DOMAIN to match the Route

```bash
ROUTE_HOST=$(oc get route gogs-http -o jsonpath='{.spec.host}')
oc set env deployment/gogs GOGS_DOMAIN="${ROUTE_HOST}"
```

### SSH access from OpenShift

OpenShift Routes only support HTTP/HTTPS. For SSH access, expose port 2222 via a NodePort:

```bash
oc patch svc gogs -p '{"spec":{"type":"NodePort"}}'
oc patch svc gogs --type='json' \
  -p='[{"op":"add","path":"/spec/ports/-",
        "value":{"name":"ssh-nodeport","port":2222,"nodePort":30022,
                 "targetPort":2222,"protocol":"TCP"}}]'
# Then: git clone ssh://git@<node-ip>:30022/<user>/<repo>.git
```

---

## OpenShift DevSpaces

To include Gogs as a component in a DevSpaces workspace, use the provided devfile:

```bash
oc devspaces workspace create --devfile deployment/devfile.yaml
```

Or register `deployment/devfile.yaml` in the DevSpaces dashboard.

---

## Directory Structure

```
gogs/
├── Containerfile              # Container image definition (UBI9-minimal base)
├── entrypoint.sh              # Startup script (init + admin provisioning)
└── deployment/
    ├── deployment.yaml        # OpenShift Deployment
    ├── service.yaml           # Service (ports 3000 + 2222)
    ├── route.yaml             # Route (HTTP) + NodePort notes (SSH)
    ├── pvc.yaml               # PersistentVolumeClaim for all Gogs data
    ├── secret.yaml            # Secret template for admin credentials
    └── devfile.yaml           # OpenShift DevSpaces devfile
```
