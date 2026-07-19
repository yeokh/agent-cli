# Running Pydantic Assistant in OpenShift Dev Spaces

This guide explains how to build a custom container image for the Pydantic
Assistant and open it as a workspace in OpenShift Dev Spaces.

## Files

| File | Purpose |
|---|---|
| `Containerfile-devspaces` | Builds the Dev Spaces image (UDI base, deps baked in, source mounted at runtime) |
| `devfile.yaml` | Defines the Dev Spaces workspace (container, port, commands, env vars) |

## Base image — why UDI?

The image is based on the **Universal Developer Image (UDI)**
(`quay.io/devfile/universal-developer-image:ubi9-latest`) rather than
`ubi9/python-312`.

`ubi9/python-312` sets `HOME=/opt/app-root/src`, which is the same directory
Dev Spaces uses as the project mount point. Dev Spaces injects IDE tooling and
config files into `$HOME` at workspace startup, causing conflicts with the
mounted source tree.

UDI sets `HOME=/home/user` (user `10001:0`) — the layout Dev Spaces expects —
and already includes `git`, `bash`, `curl`, and Python 3.11+. The production
`Containerfile` (based on `ubi9/python-312`) is unaffected and remains correct
for OpenShift deployments.

## How it works

Dev Spaces mounts the git repository into the running container at
`${PROJECT_SOURCE}` (e.g. `/projects/agent-assistant`) via `mountSources: true`
in `devfile.yaml`. The Python dependencies are pre-installed in the image so the
workspace is ready immediately — no on-start install step is needed.

The web app (`web_app.py`) runs from `${PROJECT_SOURCE}` and Dev Spaces
automatically proxies port `8081` to an HTTPS endpoint visible in the
workspace browser tab.

```
Git repo  ──mountSources──▶  /projects/agent-assistant  ──▶  python web_app.py
                                                                      │
                                                               port 8081
                                                                      │
                                                     Dev Spaces HTTPS proxy
                                                                      │
                                                              Browser tab
```

## Prerequisites

- Podman (for local image builds)
- Access to `quay.io/kenghua_yeo` (or update the image reference)
- An OpenShift cluster running Dev Spaces 3.x

---

## Step 1 — Build and push the image

Run this once, and again whenever `requirements.txt` changes:

```bash
cd /path/to/agent-assistant

podman build \
  -t quay.io/kenghua_yeo/assistant-devspaces:latest \
  -f Containerfile-devspaces .

podman push quay.io/kenghua_yeo/assistant-devspaces:latest
```

> **Tip:** The image does **not** contain source files. Rebuilding is only
> needed when Python dependencies change, not when you edit application code.

---

## Step 2 — Supply API keys (choose one option)

### Option A — Hard-code in `devfile.yaml` (dev only)

Uncomment and fill in the `Option A` env block in `devfile.yaml`:

```yaml
- name: ANTHROPIC_API_KEY
  value: sk-ant-...
```

> Not recommended for shared or production clusters.

### Option B — OpenShift Secret (recommended)

Create the secret once in the Dev Spaces namespace:

```bash
oc create secret generic assistant-api-keys \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-... \
  --from-literal=OPENAI_API_KEY=sk-...
```

Then uncomment the `Option B` (`secretKeyRef`) blocks in `devfile.yaml`.

### Option C — Web UI (no pre-configuration required)

Leave the key env vars unset. After the workspace starts, open the chat
interface Settings panel and enter your API key there. The app stores it
in memory for the session.

---

## Step 3 — Open the workspace

### Via the Dev Spaces dashboard

1. Log in to your Dev Spaces instance.
2. Click **Create Workspace**.
3. Paste the repository URL. Dev Spaces finds `devfile.yaml` at the repo
   root and uses it automatically.

### Via a direct URL

```
https://<devspaces-host>/dashboard/#/load-factory?url=<repo-url>
```

Replace `<devspaces-host>` with your cluster's Dev Spaces hostname and
`<repo-url>` with the full HTTPS URL of this repository.

---

## Step 4 — Start the app

Once the workspace is open, run the **Start Pydantic Assistant** command
from the Dev Spaces command palette (or the run button in the IDE). This
executes:

```bash
python web_app.py
```

Dev Spaces will show a notification with the proxied HTTPS URL for port
`8081`. Click it to open the chat UI in your browser.

---

## Updating dependencies

If you add packages to `requirements.txt`:

1. Rebuild and repush the image (Step 1).
2. Restart the workspace — Dev Spaces pulls the new image automatically.

Alternatively, run the **Install / update Python dependencies** command
inside the running workspace to install changes without a full rebuild:

```bash
pip install --no-cache-dir -r requirements.txt
```

---

## Environment variables reference

These can be set in `devfile.yaml` or overridden by an OpenShift Secret.

| Variable | Default | Description |
|---|---|---|
| `API_PROVIDER` | `anthropic` | Active AI provider (`anthropic`, `openai`, `openrouter`, `gemini`, `groq`, `mistral`, `openai-compatible`) |
| `MODEL` | `claude-opus-4-5` | Model name for the selected provider |
| `ANTHROPIC_API_KEY` | _(unset)_ | Anthropic API key |
| `OPENAI_API_KEY` | _(unset)_ | OpenAI or OpenAI-compatible API key |
| `OPENROUTER_API_KEY` | _(unset)_ | OpenRouter API key |
| `GEMINI_API_KEY` | _(unset)_ | Google Gemini API key |
| `GROQ_API_KEY` | _(unset)_ | Groq API key |
| `MISTRAL_API_KEY` | _(unset)_ | Mistral API key |
| `MAX_TURNS` | `50` | Maximum conversation turns per session |
| `MAX_OUTPUT_TOKENS` | `16384` | Maximum tokens per model response |
| `ALLOW_SHELL` | `true` | Allow the agent to run shell commands |
| `SHELL_TIMEOUT` | `60` | Shell command timeout in seconds |
| `PORT` | `8081` | Port the Flask server listens on |
| `HOST` | `0.0.0.0` | Bind address |

---

## Troubleshooting

**Workspace fails to start / image pull error**
Verify the image was pushed successfully:
```bash
podman pull quay.io/kenghua_yeo/assistant-devspaces:latest
```
Confirm the quay.io repository is public, or that the Dev Spaces service
account has pull credentials configured.

**Port 8081 not accessible**
Check that `python web_app.py` is running inside the workspace terminal.
The Dev Spaces endpoint only appears after the process binds to the port.

**`ModuleNotFoundError` at startup**
The image may be stale. Run the **Install / update Python dependencies**
command or rebuild the image with `--no-cache` and restart the workspace.

**API key not recognised**
Confirm the env var name matches the provider (see table above). The web
UI Settings panel shows which provider and key are currently active.
