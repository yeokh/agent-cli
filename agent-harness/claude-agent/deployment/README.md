# Build & Deploy

## Build the image

```bash
podman build -t quay.io/khyeo/claude-agent:v1 -f Containerfile .
podman login quay.io
podman push quay.io/khyeo/claude-agent:v1
```

The image supports two run modes via the `RUN_MODE` environment variable:

| `RUN_MODE` | Behaviour |
|------------|-----------|
| `agent` (default) | Headless batch run — `claude_agent.py` |
| `web` | Flask web UI on port 8080 — `web_app.py` |

---

## Test locally with Podman

**1. Create volumes:**
```bash
podman volume create claude-agent-agent
podman volume create claude-agent-input
podman volume create claude-agent-output
```

**2. Export your API key:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

**3a. Run as web UI:**
```bash
podman run --rm -it --name claude-agent \
  -p 8080:8080 \
  -e RUN_MODE=web \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -e API_PROVIDER=anthropic \
  -e MODEL=claude-haiku-4-5 \
  -v claude-agent-agent:/app/agent \
  -v claude-agent-input:/app/input \
  -v claude-agent-output:/app/output \
  quay.io/khyeo/claude-agent:v1
```
Then open http://localhost:8080 in your browser.

**3b. Run as headless agent:**
```bash
podman run --rm -it --name claude-agent \
  -e RUN_MODE=agent \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -e API_PROVIDER=anthropic \
  -e MODEL=claude-haiku-4-5 \
  -v claude-agent-agent:/app/agent \
  -v claude-agent-input:/app/input \
  -v claude-agent-output:/app/output \
  quay.io/khyeo/claude-agent:v1
```

---

## Copy files into a running container

```bash
# Using podman cp
podman cp myfile.txt claude-agent:/app/input/
podman cp ./my-job-files/. claude-agent:/app/input/

# Using oc cp (OpenShift)
oc get pods -l app=claude-agent
oc cp ./my-job-files/ <pod-name>:/app/input/
```

Since folders are backed by PVCs, files persist across pod restarts.
