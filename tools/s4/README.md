# S4 — Super Simple Storage Service

A single-container S3-compatible object storage server built on [S4](https://github.com/rh-aiservices-bu/s4), designed for:

- **Development and POC environments** — no Ceph cluster required; all data stored on a regular filesystem
- **OpenShift DevSpaces** — runs under restricted-v2 SCC with an arbitrary injected UID
- **Standalone use** — works with plain `podman run`
- **Full S3 API compatibility** — works with `aws` CLI, `boto3`, `s5cmd`, and any S3-compatible client

It combines **Ceph RADOS Gateway (RGW)** with a POSIX filesystem backend and a **React/Node.js management UI**, all in one container.

---

## Quick Start

### Build

```bash
# Standard build — downloads s4 source from GitHub and ceph-radosgw from the
# official Ceph Reef repo:
podman build -t s4-server:latest .

# Pin a specific s4 release:
podman build --build-arg S4_VERSION=0.3.2 -t s4-server:latest .
```

### Disconnected / Air-gapped Build

Download the s4 source tarball on a connected machine:

```bash
curl -fsSL https://github.com/rh-aiservices-bu/s4/archive/refs/tags/v0.3.2.tar.gz \
     -o s4-src.tar.gz
```

In `Containerfile`, uncomment the `COPY s4-src.tar.gz` line (Option B) and comment out the `curl` block.

For the Ceph repo, mirror `https://download.ceph.com/rpm-reef/el9/` internally and update the URL in the `Containerfile`.

### Run Standalone

```bash
# Default credentials (s4admin / s4secret), no UI auth:
podman run --rm -p 5000:5000 -p 7480:7480 \
  -v s4-data:/var/lib/ceph/radosgw \
  s4-server:latest

# Custom credentials + UI authentication:
podman run --rm -p 5000:5000 -p 7480:7480 \
  -e AWS_ACCESS_KEY_ID=mykey \
  -e AWS_SECRET_ACCESS_KEY=mysecret \
  -e UI_USERNAME=admin \
  -e UI_PASSWORD=changeme \
  -e COOKIE_REQUIRE_HTTPS=false \
  -v s4-data:/var/lib/ceph/radosgw \
  s4-server:latest
```

### Use the S3 API

```bash
export AWS_ACCESS_KEY_ID=s4admin
export AWS_SECRET_ACCESS_KEY=s4secret
export AWS_ENDPOINT_URL=http://localhost:7480

# AWS CLI
aws s3 mb s3://my-bucket
aws s3 cp myfile.txt s3://my-bucket/

# s5cmd (bundled in the image)
podman exec <container> s5cmd ls
```

### Open the Web UI

Navigate to [http://localhost:5000](http://localhost:5000).

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | `s4admin` | S3 admin access key ID |
| `AWS_SECRET_ACCESS_KEY` | `s4secret` | S3 admin secret access key |
| `AWS_DEFAULT_REGION` | `us-east-1` | S3 region |
| `AWS_S3_ENDPOINT` | `http://localhost:7480` | Internal RGW endpoint (keep localhost) |
| `PORT` | `5000` | Web UI listen port |
| `UI_USERNAME` | `""` | Web UI login username (empty = no auth) |
| `UI_PASSWORD` | `""` | Web UI login password (empty = no auth) |
| `JWT_SECRET` | `""` | JWT signing secret (auto-generated if empty) |
| `JWT_EXPIRATION_HOURS` | `8` | JWT token lifetime |
| `COOKIE_REQUIRE_HTTPS` | `true` | Require HTTPS for session cookies (set `false` for local dev) |
| `LOCAL_STORAGE_PATHS` | `""` | Comma-separated paths to expose in file browser |
| `MAX_FILE_SIZE_GB` | `20` | Maximum single-file upload size (GB) |
| `MAX_CONCURRENT_TRANSFERS` | `2` | Maximum parallel transfers |

---

## Architecture

Two processes run under **supervisord**:

| Process | Port | Description |
|---|---|---|
| `radosgw` | 7480 | Ceph RGW daemon — S3-compatible API with POSIX+SQLite backend |
| `nodejs` | 5000 | Node.js/Fastify server — serves the React UI and proxies S3 operations |

Both processes log to stdout/stderr, visible via `podman logs`.

### Ceph configuration note

This image uses Ceph 18 (Reef) packages with the **POSIX filter** (`rgw filter = posix`) and the **dbstore** metadata backend. No Ceph monitors, OSDs, or cluster setup are required — all data is stored as ordinary files under `/var/lib/ceph/radosgw/`.

---

## OpenShift Deployment

### Create resources

```bash
# Create namespace:
oc new-project s4

# Apply manifests:
oc apply -f deployment/pvc.yaml
oc apply -f deployment/secret.yaml
oc apply -f deployment/deployment.yaml
oc apply -f deployment/service.yaml
oc apply -f deployment/route.yaml
```

### Set credentials via Secret

```bash
oc create secret generic s4-secret \
  --from-literal=AWS_ACCESS_KEY_ID=s4admin \
  --from-literal=AWS_SECRET_ACCESS_KEY=changeme \
  --from-literal=UI_USERNAME=admin \
  --from-literal=UI_PASSWORD=changeme \
  --dry-run=client -o yaml | oc apply -f -
```

### Get the web UI URL

```bash
oc get route s4-ui -o jsonpath='{.spec.host}'
```

### Get the S3 API URL

```bash
S3_HOST=$(oc get route s4-s3 -o jsonpath='{.spec.host}')
export AWS_ENDPOINT_URL="https://${S3_HOST}"
aws s3 ls
```

### Update COOKIE_REQUIRE_HTTPS for the Route

The OpenShift Route terminates TLS externally. Update the deployment:

```bash
oc set env deployment/s4 COOKIE_REQUIRE_HTTPS=true
```

### Enable local filesystem browser (optional)

Uncomment the `s4-local-storage` PVC and volume mount in `deployment/pvc.yaml` and `deployment/deployment.yaml`, then:

```bash
oc set env deployment/s4 LOCAL_STORAGE_PATHS=/opt/app-root/src/data
```

---

## OpenShift DevSpaces

To include S4 as a component in a DevSpaces workspace:

```bash
oc devspaces workspace create --devfile deployment/devfile.yaml
```

Or register `deployment/devfile.yaml` in the DevSpaces dashboard.

---

## Directory Structure

```
s4/
├── Containerfile              # Multi-stage build: ubi9/nodejs-20 (build) + ubi9/nodejs-20 (runtime)
├── entrypoint.sh              # Startup script (first-run user creation → supervisord)
├── ceph.conf                  # Ceph RGW configuration (POSIX filter + dbstore backend)
├── supervisord.conf           # Process supervisor config (radosgw + nodejs)
└── deployment/
    ├── deployment.yaml        # OpenShift Deployment
    ├── service.yaml           # Service (ports 5000 + 7480)
    ├── route.yaml             # Routes (web UI + S3 API)
    ├── pvc.yaml               # PVCs (RGW data + optional local storage)
    ├── secret.yaml            # Secret template for credentials
    └── devfile.yaml           # OpenShift DevSpaces devfile
```
