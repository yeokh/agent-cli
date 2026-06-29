# Build & Deploy

## Build the image

```bash
podman build -t quay.io/<your-org>/pydantic-agent:v1 -f Containerfile .
podman login quay.io
podman push quay.io/<your-org>/pydantic-agent:v1
```

The image supports two run modes controlled by the `RUN_MODE` environment variable:

| `RUN_MODE` | Behaviour |
|------------|-----------|
| `agent` (default) | Headless batch run — `pydantic_agent.py` |
| `web` | Flask web UI on port 8080 — `web_app.py` |

---

## Test locally with Podman

**1. Create volumes:**
```bash
podman volume create pydantic-agent-agent
podman volume create pydantic-agent-input
podman volume create pydantic-agent-output
```

**2. Export an API key for your chosen provider:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
# or
export OPENAI_API_KEY="sk-..."
# or no key needed for openai-compatible (Ollama/vLLM)
```

**3a. Run as web UI:**
```bash
podman run --rm -it --name pydantic-agent \
  -p 8080:8080 \
  -e RUN_MODE=web \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -e API_PROVIDER=anthropic \
  -e MODEL=claude-haiku-4-5 \
  -v pydantic-agent-agent:/app/agent \
  -v pydantic-agent-input:/app/input \
  -v pydantic-agent-output:/app/output \
  quay.io/<your-org>/pydantic-agent:v1
```
Then open http://localhost:8080 in your browser.

**3b. Run as headless agent:**
```bash
podman run --rm -it --name pydantic-agent \
  -e RUN_MODE=agent \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -e API_PROVIDER=anthropic \
  -e MODEL=claude-haiku-4-5 \
  -v pydantic-agent-agent:/app/agent \
  -v pydantic-agent-input:/app/input \
  -v pydantic-agent-output:/app/output \
  quay.io/<your-org>/pydantic-agent:v1
```

**3c. Run with a local Ollama model (no key needed):**
```bash
podman run --rm -it --name pydantic-agent \
  -p 8080:8080 \
  -e RUN_MODE=web \
  -e API_PROVIDER=openai-compatible \
  -e OPENAI_BASE_URL=http://host.containers.internal:11434/v1 \
  -e MODEL=llama3.2 \
  -v pydantic-agent-agent:/app/agent \
  -v pydantic-agent-input:/app/input \
  -v pydantic-agent-output:/app/output \
  quay.io/<your-org>/pydantic-agent:v1
```

> `host.containers.internal` resolves to the host machine from inside the container.
> Use this instead of `localhost` when Ollama or vLLM is running on your host.

---

## Copy files into a running container

```bash
# Using podman cp
podman cp myfile.txt pydantic-agent:/app/input/
podman cp ./my-job-files/. pydantic-agent:/app/input/

# Using oc cp (OpenShift)
oc get pods -l app=pydantic-agent
oc cp ./my-job-files/ <pod-name>:/app/input/
```

Since folders are backed by PVCs, files persist across pod restarts.
