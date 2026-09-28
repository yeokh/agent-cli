# devpi PyPI Server

A single-container private PyPI server built on [devpi](https://github.com/devpi/devpi), designed for:

- **Disconnected / air-gapped environments** — packages are pre-loaded at image build time
- **OpenShift DevSpaces** — runs under restricted-v2 SCC with an arbitrary injected UID
- **Standalone use** — works with plain `podman run`
- **Browser management** — optional [ttyd](https://github.com/tsl0922/ttyd) web terminal for interactive devpi administration

---

## Quick Start

### Build

```bash
# Standard build — downloads packages from requirements.txt during build:
podman build -t devpi-server:latest .

# Custom requirements file:
podman build --build-arg REQUIREMENTS_FILE=my-reqs.txt -t devpi-server:latest .
```

### Disconnected / Air-gapped Build

On a **connected** machine, pre-download all packages and their dependencies:

```bash
pip download -r requirements.txt -d ./packages/
```

Then in `Containerfile`, uncomment the `COPY packages/ /packages/` line (Option B) and build without internet access:

```bash
podman build -t devpi-server:latest .
```

### Run Standalone

```bash
# devpi only (port 3141):
podman run --rm -p 3141:3141 \
  -v devpi-data:/data/devpi-server \
  devpi-server:latest

# devpi + ttyd web terminal (ports 3141 + 7681):
podman run --rm -p 3141:3141 -p 7681:7681 \
  -e DEVPI_MODE=ttyd \
  -v devpi-data:/data/devpi-server \
  devpi-server:latest
```

### Configure pip

```bash
pip config set global.index-url  http://localhost:3141/root/local/+simple/
pip config set global.trusted-host localhost
```

Or per-command:

```bash
pip install --index-url http://localhost:3141/root/local/+simple/ requests
```

---

## Pre-loading Packages

Edit `requirements.txt` to specify packages you want available offline:

```text
requests
numpy
pandas
scikit-learn
```

All packages **and their dependencies** are downloaded into `/packages/` during `podman build` and automatically uploaded into the devpi index on first startup.

### Adding Packages at Runtime

With `DEVPI_MODE=ttyd`, open the browser terminal at port 7681 and:

```bash
# Upload a local wheel:
devpi upload /packages/mypackage-1.0-py3-none-any.whl

# Download and add a new package from PyPI (connected mode):
pip download somepackage -d /tmp/dl/
devpi upload /tmp/dl/*.whl
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DEVPI_MODE` | `server` | `server` (devpi only) or `ttyd` (devpi + web terminal) |
| `DEVPI_PORT` | `3141` | devpi listen port |
| `DEVPI_USER` | `root` | devpi admin username |
| `DEVPI_PASSWORD` | `""` | devpi admin password |
| `DEVPI_INDEX` | `local` | staging index name under `DEVPI_USER` |
| `DEVPI_BASES` | `""` | Index bases — empty = air-gapped; `root/pypi` = proxy to upstream |
| `DEVPI_UPSTREAM_URL` | `https://pypi.org/simple/` | Upstream mirror URL (only if `DEVPI_BASES=root/pypi`) |
| `PACKAGES_DIR` | `/packages` | Directory of package files to upload on startup |

---

## Operating Modes

### Air-gapped (default)

```bash
DEVPI_BASES=""   # pure staging index, no upstream fallback
```

Only packages pre-loaded at build time (or manually uploaded) are available.

### Proxied (connected)

```bash
DEVPI_BASES=root/pypi
DEVPI_UPSTREAM_URL=https://pypi.org/simple/
```

The local index inherits from a PyPI mirror. Packages not in the local index are fetched from upstream and cached.

---

## OpenShift Deployment

### Create resources

```bash
# Create namespace (if needed):
oc new-project devpi

# Apply manifests:
oc apply -f deployment/pvc.yaml
oc apply -f deployment/secret.yaml
oc apply -f deployment/deployment.yaml
oc apply -f deployment/service.yaml
oc apply -f deployment/route.yaml
```

### Set admin password via Secret

```bash
oc create secret generic devpi-secret \
  --from-literal=DEVPI_PASSWORD=changeme \
  --dry-run=client -o yaml | oc apply -f -
```

### Get the PyPI index URL

```bash
oc get route devpi-pypi -o jsonpath='{.spec.host}'
# Configure pip:
pip config set global.index-url https://<route-host>/root/local/+simple/
```

### Open the admin terminal

```bash
oc get route devpi-terminal -o jsonpath='{.spec.host}'
# Open in browser: https://<route-host>
```

---

## OpenShift DevSpaces

To include devpi as a component in a DevSpaces workspace, use the provided devfile:

```bash
oc devspaces workspace create --devfile deployment/devfile.yaml
```

Or register `deployment/devfile.yaml` in the DevSpaces dashboard.

---

## Directory Structure

```
devpi/
├── Containerfile              # Container image definition
├── entrypoint.sh              # Startup script (devpi init + package upload)
├── requirements.txt           # Packages to pre-load (customize this)
└── deployment/
    ├── deployment.yaml        # OpenShift Deployment
    ├── service.yaml           # Service (ports 3141 + 7681)
    ├── route.yaml             # Routes (devpi-pypi + devpi-terminal)
    ├── pvc.yaml               # PersistentVolumeClaim for devpi data
    ├── secret.yaml            # Secret template for admin password
    └── devfile.yaml           # OpenShift DevSpaces devfile
```
