# goose on OpenShift

Run [goose](https://github.com/block/goose) as a generic AI agent on OpenShift, using your own LLM provider and API keys. This follows **Red Hat Option 2** ([install `goose` only, not `goose-redhat`](https://access.redhat.com/articles/7142302)).

The pod stays running in the background; you connect interactively with `oc rsh` and run `goose session`.

## What persists across redeployments

| Resource | Purpose | Keep when redeploying? |
|----------|---------|------------------------|
| PVC `goose-config` | Provider config, `secrets.yaml`, sessions, custom providers | **Yes** |
| Secret `goose-api-keys` | API keys injected as env vars (optional) | **Yes** |
| Pod `goose` | Container runtime | **No** — delete and recreate with a new image |

Configuration written by `goose configure` is stored on the PVC at `/home/goose/.config/goose`. Redeploying a new image does not touch that volume.

## Prerequisites

- OpenShift cluster access and the `oc` CLI
- Permission to create Pods, PVCs, and Secrets in a project
- Egress from the cluster to your LLM provider API (OpenAI, Anthropic, etc.)
- `podman` or `docker` on your workstation to build and push the image
- A [Quay.io](https://quay.io) account with push access to `quay.io/kenghua_yeo/goose`

## 1. Log in and select a project

All `oc` commands below use your **current project**. Set it once before building and deploying:

```bash
oc login <api-server-url>

# Create a new project (also selects it as the current project):
oc new-project goose

# Or select an existing project:
# oc project <your-project>
```

Confirm the active project:

```bash
oc project
```

The pod manifest pulls the image from `quay.io/kenghua_yeo/goose:latest`. Use `oc project` to choose where the pod is deployed — the image reference does not change.

## 2. Build and push the image to Quay

From this directory (`goose/`):

```bash
export IMAGE=quay.io/kenghua_yeo/goose:latest

podman build -t "${IMAGE}" -f Containerfile .

podman login quay.io
podman push "${IMAGE}"
```

If the Quay repository is **private**, create an image pull secret in your OpenShift project before deploying:

```bash
oc create secret docker-registry quay-pull-secret \
  --docker-server=quay.io \
  --docker-username=<quay-username> \
  --docker-password=<quay-password> \
  --docker-email=<email>

oc secrets link default quay-pull-secret --for=pull
```

### Test locally with `podman run` (optional)

You can test the image on your workstation before deploying to OpenShift. Use a named Podman volume to persist goose configuration the same way the OpenShift PVC does.

Create a volume (once):

```bash
podman volume create goose-config
```

Initial setup:

```bash
podman run --rm -it \
  -v goose-config:/home/goose/.config/goose \
  -v "$PWD:/home/goose/workspace:Z" \
  "${IMAGE}" \
  configure
```

Run goose (interactive CLI):

```bash
podman run --rm -it \
  -v goose-config:/home/goose/.config/goose \
  -v "$PWD:/home/goose/workspace:Z" \
  "${IMAGE}"
```

Or pass a subcommand explicitly:

```bash
podman run --rm -it \
  -v goose-config:/home/goose/.config/goose \
  -v "$PWD:/home/goose/workspace:Z" \
  "${IMAGE}" \
  session
```

Pass provider settings via environment variables instead of `configure`:

```bash
podman run --rm -it \
  -e OPENAI_API_KEY \
  -e GOOSE_PROVIDER=openai \
  -e GOOSE_MODEL=gpt-4o \
  -v goose-config:/home/goose/.config/goose \
  -v "$PWD:/home/goose/workspace:Z" \
  "${IMAGE}" \
  session
```

For a long-running container (similar to the OpenShift pod):

```bash
podman run -d \
  --name goose \
  -v goose-config:/home/goose/.config/goose \
  -v "$PWD:/home/goose/workspace:Z" \
  "${IMAGE}" \
  sleep infinity

podman exec -it goose bash
```

| Mount | Persists |
|-------|----------|
| `goose-config:/home/goose/.config/goose` | Yes — config, secrets, custom providers, sessions |
| `$PWD:/home/goose/workspace` | On your host filesystem |
| Container | No — stop, remove, and recreate freely |

To retest after rebuilding the image:

```bash
podman stop goose
podman rm goose
podman build -t "${IMAGE}" -f Containerfile .
podman run -d --name goose \
  -v goose-config:/home/goose/.config/goose \
  -v "$PWD:/home/goose/workspace:Z" \
  "${IMAGE}" \
  sleep infinity

podman exec -it goose goose info
```

**Note:** You do not need `--entrypoint goose`. The image entrypoint sets up the environment and forwards arguments to `goose`. Use `--entrypoint goose` only if you want to bypass that setup entirely.

## 3. Deploy persistent storage and the pod

```bash
oc apply -f openshift/pvc.yaml
oc apply -f openshift/pod.yaml
```

Wait for the pod to be ready:

```bash
oc get pod goose -w
```

## 4. Initial setup (one time)

Connect to the pod:

```bash
oc rsh goose
```

### Option A — Interactive configure (recommended)

Inside the pod:

```bash
goose configure
```

Follow the prompts to select your provider, enter API credentials, and choose a model. Settings are saved to the PVC:

- `~/.config/goose/config.yaml` — provider and extension settings
- `~/.config/goose/secrets.yaml` — API keys (keyring is disabled in containers)

Verify:

```bash
goose --version
goose info
```

Exit the shell when done:

```bash
exit
```

### Option B — API keys via OpenShift Secret

Create a secret (outside the pod):

```bash
oc create secret generic goose-api-keys \
  --from-literal=OPENAI_API_KEY=<your_key>
```

Uncomment the env vars in `openshift/pod.yaml`:

```yaml
- name: GOOSE_PROVIDER
  value: openai
- name: GOOSE_MODEL
  value: gpt-4o
- name: OPENAI_API_KEY
  valueFrom:
    secretKeyRef:
      name: goose-api-keys
      key: OPENAI_API_KEY
```

Reapply the pod:

```bash
oc delete pod goose --wait=true
oc apply -f openshift/pod.yaml
```

Then verify with `oc rsh goose` and `goose info`.

### Custom OpenAI-compatible provider

Use this when your LLM exposes an OpenAI-compatible API (vLLM, LiteLLM, an internal gateway, etc.) and is not a built-in goose provider. A starter template lives at `custom_providers/example-openai-compatible.json` in this repo.

**Note:** That example file is **not** copied into the image. The `Containerfile` only bakes in `config.yaml` and `entrypoint.sh`; it creates an empty `custom_providers/` directory at build time. Copying a JSON file into the image would make goose **discover** the provider, but would **not** activate it automatically — you must still edit the endpoint, set the API key, and select the provider and model.

On OpenShift, the PVC is mounted at `/home/goose/.config/goose`, which replaces that directory in the container. Custom provider JSON must live on the **PVC** (created via `oc rsh`), not only in the image.

Inside the pod, create a JSON file on the persistent volume (or copy and edit the repo example):

```bash
oc rsh goose
mkdir -p ~/.config/goose/custom_providers
cat > ~/.config/goose/custom_providers/my-provider.json <<'EOF'
{
  "name": "my_provider",
  "engine": "openai",
  "display_name": "My Provider",
  "api_key_env": "MY_PROVIDER_API_KEY",
  "base_url": "https://api.example.com/v1",
  "models": [{"name": "my-model", "context_limit": 128000}],
  "requires_auth": true,
  "supports_streaming": true
}
EOF
```

Activate the provider (pick one):

```bash
# Option 1 — environment variables (also set MY_PROVIDER_API_KEY via Secret or oc rsh)
export GOOSE_PROVIDER=my_provider
export GOOSE_MODEL=my-model

# Option 2 — interactive
goose configure
```

Verify with `goose info`.

## 5. Daily use via `oc rsh`

```bash
oc rsh goose
cd ~/workspace
goose session
```

The `workspace` directory is an `emptyDir` — files there are lost when the pod is recreated. Clone or copy project files into `~/workspace` each session, or mount additional PVCs if you need persistent project data.

Other useful commands inside the pod:

```bash
goose info          # show active provider and model
goose configure     # change provider or model
goose run <recipe>  # run a non-interactive recipe
```

## 6. Redeploy a new image (setup persists)

When you rebuild the image, only replace the pod. **Do not delete the PVC or Secret.**

Ensure you are in the same project:

```bash
oc project
```

Build and push the updated image to Quay:

```bash
export IMAGE=quay.io/kenghua_yeo/goose:latest

podman build -t "${IMAGE}" -f Containerfile .
podman push "${IMAGE}"
```

Recreate the pod (PVC is reused automatically):

```bash
oc delete pod goose --wait=true
oc apply -f openshift/pod.yaml
oc get pod goose -w
```

Confirm your settings survived:

```bash
oc rsh goose
goose info
```

## Troubleshooting

### `oc rsh` fails or pod is not ready

```bash
oc describe pod goose
oc logs goose
```

### Image pull errors

Confirm the image exists on Quay and the cluster can pull from `quay.io`:

```bash
podman pull quay.io/kenghua_yeo/goose:latest
oc describe pod goose
```

If the repository is private, confirm the pull secret is linked:

```bash
oc get secret quay-pull-secret
oc secrets link default quay-pull-secret --for=pull
```

### Provider not configured

```bash
oc rsh goose
ls -la ~/.config/goose/
goose configure
```

### API key errors

- With Option A: check `~/.config/goose/secrets.yaml` inside the pod.
- With Option B: check the secret exists: `oc get secret goose-api-keys`.

### Permission errors on config directory

The image is built for OpenShift's arbitrary UID (group 0, `g+rwX` on `/home/goose`). If you see write errors, confirm the PVC mount path is `/home/goose/.config/goose` as in `openshift/pod.yaml`.

### Cannot reach LLM API

Confirm cluster egress allows HTTPS to your provider. Check corporate proxies and NetworkPolicies.

### `sudo` does not work inside the pod

Expected on OpenShift — the container runs as an arbitrary UID without elevated privileges. Most goose developer tasks work without sudo.

## ttyd Web Terminal Image

`Containerfile-ttyd` builds a variant of the goose image that exposes a browser-based terminal via [ttyd](https://github.com/tsl0922/ttyd). Instead of connecting with `oc rsh`, you open a URL and get a `goose session` directly in the browser.

### Build and run locally

```bash
export IMAGE=goose-ttyd:v1

podman build -t "${IMAGE}" -f Containerfile-ttyd .

podman volume create goose-config
podman volume create goose-workspace

podman run --rm -p 7681:7681 \
  -e OPENAI_API_KEY=mykey \
  -e GOOSE_PROVIDER=openai \
  -e GOOSE_MODEL=gpt-4o \
  -v goose-config:/home/goose/.config/goose \
  -v goose-workspace:/home/goose/workspace \
  "${IMAGE}"
```

Open http://localhost:7681 in your browser to start a goose session.

### Differences from the base image

| Aspect | `Containerfile` | `Containerfile-ttyd` |
|--------|----------------|----------------------|
| Entry point | `entrypoint.sh` → `goose` | `ttyd` → `goose session` |
| Access method | `oc rsh` / `podman exec` | Browser at `:7681` |
| Extra binary | — | `ttyd` 1.7.7 static binary |
| Volumes | `goose-config` | `goose-config`, `goose-workspace` |
| Port | none | 7681 |

### OpenShift deployment notes

- Runs as uid 1001; no privileged SCC required.
- Expose port 7681 via a Service and Route.
- For authentication, add `--credential user:pass` to the `CMD` for basic auth, or front the Route with an OAuth proxy.
- For persistent storage, mount PVCs at `/home/goose/.config/goose` and `/home/goose/workspace`.
- To allow multiple concurrent browser sessions, remove `--once` (it is not set by default in the current `CMD`).

### Use a plain shell instead

To get a bash prompt (with `goose` on `PATH`) rather than launching directly into `goose session`, override the command at runtime:

```bash
podman run --rm -p 7681:7681 \
  -e OPENAI_API_KEY=mykey \
  -v goose-config:/home/goose/.config/goose \
  goose-ttyd:v1 \
  ttyd --port 7681 --writable bash
```


podman run --rm -p 7681:7681 -e GOOSE_PROVIDER=openai -e GOOSE_MODEL=gpt-5.4-nano \
  -v goose-config:/home/goose/.config/goose   -v goose-workspace:/home/goose/workspace \
       quay.io/kenghua_yeo/goose-ttyd:v1 \
       ttyd --port 7681 --writable /bin/bash

# export OPENAI_API_KEY=sk-proj-o-xxx
# goose configure
# goose 
  /model gpt-5.4-nano 


## File reference

| File | Purpose |
|------|---------|
| `Containerfile` | Image build definition (UBI 9 + EPEL `goose` RPM) |
| `Containerfile-ttyd` | Variant with ttyd web terminal frontend on port 7681 |
| `config.yaml` | Default extensions baked into the image |
| `entrypoint.sh` | Sets `GOOSE_DISABLE_KEYRING`, creates config dirs, forwards args to `goose` |
| `openshift/pvc.yaml` | Persistent volume for goose configuration |
| `openshift/pod.yaml` | Long-running pod for `oc rsh` |
| `openshift/examples.yaml` | Additional examples (Job) |
| `custom_providers/example-openai-compatible.json` | Template for custom providers (not copied into image; see §4) |

## Security notes

- Do not commit API keys to git.
- Prefer OpenShift Secrets or `goose configure` (stored on the PVC) over hardcoding keys in manifests.
- The pod runs with `allowPrivilegeEscalation: false` and drops all capabilities.
- `GOOSE_DISABLE_KEYRING=1` is set because containers have no system keyring.
