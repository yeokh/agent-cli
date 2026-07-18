# Pydantic Assistant — Build & Deploy

## Files in this folder

| File | Purpose |
|------|---------|
| `pvc.yaml` | Three PersistentVolumeClaims (shared by both deployment variants) |
| `secret-api-keys.yaml` | API key secret (shared by both variants) |
| `deployment.yaml` | Basic deployment — no authentication |
| `service.yaml` | Service for the basic deployment (port 8081) |
| `route.yaml` | OpenShift Route with edge TLS |
| `oauth-serviceaccount.yaml` | ServiceAccount that acts as the OAuth client |
| `oauth-secret-proxy.yaml` | Session cookie secret for the OAuth proxy |
| `oauth-deployment.yaml` | Deployment with OpenShift OAuth proxy sidecar |
| `oauth-service.yaml` | Service for the OAuth deployment (port 4443) |
| `oauth-route.yaml` | OpenShift Route with reencrypt TLS |

---

## 1. Build the image

```bash
cd agent-coworker/

podman build -t quay.io/<your-org>/pydantic-assistant:latest -f Containerfile .
podman login quay.io
podman push quay.io/<your-org>/pydantic-assistant:latest
```

Replace `<your-org>` with your Quay.io organisation or username.
Update the `image:` field in `deployment.yaml` and `oauth-deployment.yaml` to match.

---

## 2. Run standalone with Podman (3 named volumes)

```bash
# Create persistent volumes
podman volume create pydantic-agent
podman volume create pydantic-input
podman volume create pydantic-output

# Set your API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Run
podman run --rm -it --name pydantic-assistant \
  -p 8081:8081 \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -e API_PROVIDER=anthropic \
  -e MODEL=claude-opus-4-5 \
  -v pydantic-agent:/app/agent \
  -v pydantic-input:/app/input \
  -v pydantic-output:/app/output \
  quay.io/<your-org>/pydantic-assistant:latest
```

Open **http://localhost:8081** in your browser.

To pre-populate the agent folder before first run:

```bash
podman run --rm \
  -v pydantic-agent:/app/agent \
  -v ./agent:/src:ro \
  ubi9/python-312 cp -r /src/. /app/agent/
```

---

## 3. Deploy to OpenShift — Basic (no authentication)

Anyone who can reach the Route URL will have full access to the chat UI.
Suitable for internal/lab use on a cluster that already enforces network-level access control.

### 3a. Set the target namespace

```bash
oc project <your-namespace>
```

### 3b. Create the PersistentVolumeClaims

```bash
oc apply -f pvc.yaml
```

### 3c. Create the API key secret

Edit `secret-api-keys.yaml` and fill in at least one API key, then:

```bash
oc apply -f secret-api-keys.yaml
```

Alternatively, create the secret from environment variables to avoid storing keys in YAML:

```bash
oc create secret generic pydantic-api-keys \
  --from-literal=ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY"
```

### 3d. Deploy

```bash
oc apply -f deployment.yaml
oc apply -f service.yaml
oc apply -f route.yaml
```

### 3e. Get the URL

```bash
oc get route pydantic-assistant -o jsonpath='{.spec.host}'
```

Open `https://<route-host>` in your browser.

### Useful commands

```bash
# Watch rollout
oc rollout status deployment/pydantic-assistant

# View logs
oc logs -f deployment/pydantic-assistant

# Copy files into the input volume
oc cp ./myfile.txt <pod-name>:/app/input/

# Scale down / up
oc scale deployment/pydantic-assistant --replicas=0
oc scale deployment/pydantic-assistant --replicas=1
```

---

## 4. Deploy to OpenShift — With OAuth (OpenShift login required)

This variant adds an **OpenShift OAuth proxy sidecar** in front of the application.
Users must log in with their OpenShift credentials before accessing the chat UI.

Architecture:

```
Browser
  │  HTTPS → Route (reencrypt TLS)
  ▼
oauth-proxy sidecar (port 4443)
  │  authenticates against OpenShift OAuth server
  │  HTTP → localhost:8081
  ▼
pydantic-assistant container (port 8081, bound to 127.0.0.1 only)
```

### 4a. Generate the proxy session secret

```bash
SESSION_SECRET=$(openssl rand -base64 32)
```

Edit `oauth-secret-proxy.yaml` and replace the placeholder with the generated value, then apply:

```bash
oc apply -f oauth-secret-proxy.yaml
```

Or create it directly:

```bash
oc create secret generic pydantic-proxy-secret \
  --from-literal=session_secret="$SESSION_SECRET"
```

### 4b. Create the ServiceAccount

```bash
oc apply -f oauth-serviceaccount.yaml
```

OpenShift automatically creates an `OAuthClient` for the ServiceAccount.
The redirect URI annotation on the ServiceAccount points to the Route created in step 4e.

### 4c. Create the PVCs and API key secret (if not already done)

```bash
oc apply -f pvc.yaml
oc apply -f secret-api-keys.yaml   # or use oc create secret as above
```

### 4d. Deploy

```bash
oc apply -f oauth-deployment.yaml
oc apply -f oauth-service.yaml
```

OpenShift detects the `service.alpha.openshift.io/serving-cert-secret-name` annotation on the
Service and automatically creates the TLS Secret `pydantic-assistant-tls` signed by the cluster CA.
The OAuth proxy mounts this secret for its HTTPS listener.

> Wait a few seconds for OpenShift to create the TLS secret before the pods become ready.

### 4e. Create the Route

```bash
oc apply -f oauth-route.yaml
```

### 4f. Grant the ServiceAccount permission to use OAuth

```bash
oc adm policy add-cluster-role-to-user system:auth-delegator \
  -z pydantic-assistant
```

This allows the OAuth proxy to validate tokens against the OpenShift API server.

### 4g. Get the URL

```bash
oc get route pydantic-assistant-oauth -o jsonpath='{.spec.host}'
```

Open `https://<route-host>` — you will be redirected to the OpenShift login page first.

### Optional: restrict access to specific users or groups

By default any authenticated OpenShift user can access the app.
To restrict to users who have `get pods` permission in the namespace, uncomment the
`--openshift-sar` argument in `oauth-deployment.yaml`:

```yaml
- --openshift-sar={"namespace":"<your-namespace>","resource":"pods","verb":"get"}
```

Then grant the role to specific users:

```bash
oc adm policy add-role-to-user view <username> -n <your-namespace>
```

---

## 5. Environment variables reference

| Variable | Default | Description |
|----------|---------|-------------|
| `API_PROVIDER` | `anthropic` | LLM provider |
| `MODEL` | `claude-opus-4-5` | Model ID |
| `MAX_TURNS` | `50` | Max tool-call iterations per chat turn |
| `MAX_OUTPUT_TOKENS` | `16384` | Token budget per model response |
| `ALLOW_SHELL` | `true` | Set `false` to disable `run_command` |
| `SHELL_TIMEOUT` | `60` | Shell command timeout (seconds) |
| `DISABLED_TOOLS` | _(empty)_ | Comma-separated tool names to disable |
| `PORT` | `8081` | Flask bind port |
| `HOST` | `0.0.0.0` | Flask bind address (`127.0.0.1` in OAuth variant) |
| `AGENT_DIR` | `/app/agent` | Path to the agent volume |
| `INPUT_DIR` | `/app/input` | Path to the input volume |
| `OUTPUT_DIR` | `/app/output` | Path to the output volume |

---

## 6. Persistent volumes

| PVC | Mount | Default size | Contents |
|-----|-------|-------------|----------|
| `pydantic-agent-pvc` | `/app/agent` | 1 Gi | `instruction.md` and skill `.md` files |
| `pydantic-input-pvc` | `/app/input` | 5 Gi | Documents and data files for the AI to read |
| `pydantic-output-pvc` | `/app/output` | 5 Gi | Files written by the AI assistant |

Adjust the storage sizes in `pvc.yaml` before first apply — PVC sizes cannot be
reduced after creation (expansion is possible on most storage classes).

---

## 7. Updating the image

```bash
# Build and push new image
podman build -t quay.io/<your-org>/pydantic-assistant:v2 -f Containerfile .
podman push quay.io/<your-org>/pydantic-assistant:v2

# Update the deployment (triggers a rolling restart)
oc set image deployment/pydantic-assistant \
  pydantic-assistant=quay.io/<your-org>/pydantic-assistant:v2

# Or for the OAuth variant:
oc set image deployment/pydantic-assistant-oauth \
  pydantic-assistant=quay.io/<your-org>/pydantic-assistant:v2
```

Data in the three volumes is preserved across image updates.
