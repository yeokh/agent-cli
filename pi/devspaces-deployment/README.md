# pi Coding Agent — OpenShift Dev Spaces Deployment

Deploys the pi AI coding agent as an **OpenShift Dev Spaces** workspace.  
Dev Spaces injects VS Code server automatically — users run `pi` from the integrated terminal.

## Architecture

```
Dev Spaces (Eclipse Che)
├── VS Code server sidecar     ← injected by Dev Spaces automatically
│     └── [browser IDE + terminal]
│                │
└── pi container (workspace)   ← Containerfile-devspaces
      ├── pi CLI
      ├── ripgrep, fd, git, jq, vim, gh-cli, ...
      ├── /projects             ← workspace PVC (cloned repo)
      └── /home/user/.pi/agent ← pi PVC (sessions, settings, extensions)
```

**Key difference from RHOAI Workbench**: the container image does NOT include an IDE or web terminal. Dev Spaces provides VS Code via a sidecar. Users interact with pi through the VS Code integrated terminal.

## Files

| File | Purpose |
|---|---|
| `Containerfile-devspaces` | Developer container image (pi + dev tools) |
| `devfile.yaml` | Workspace definition — image, volumes, env vars, commands |
| `devspaces-deployment/secret-api-keys.yaml` | LLM provider API keys secret |
| `devspaces-deployment/README.md` | This file |

---

## Step 1 — Build and push the image

```bash
# From the repo root
podman build -t quay.io/<your-org>/pi-devspaces:v1 -f Containerfile-devspaces .
podman push quay.io/<your-org>/pi-devspaces:v1
```

Update the `image:` field in `devfile.yaml` to match your registry path.

---

## Step 2 — Set up API keys

Choose one of these approaches:

### Option A — Dev Spaces User Preferences (recommended for personal use)

In the Dev Spaces dashboard:  
**User icon → User Preferences → Environment Variables → Add variable**

Add each key you need (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, etc.).  
Dev Spaces injects these into every workspace automatically — no YAML needed.

### Option B — OpenShift Secret (recommended for team/shared namespaces)

Edit `devspaces-deployment/secret-api-keys.yaml` with real key values, then apply it in your Dev Spaces namespace:

```bash
# Dev Spaces workspaces run in your user namespace, e.g. <username>-devspaces
oc project <username>-devspaces
oc apply -f devspaces-deployment/secret-api-keys.yaml
```

The secret has the annotation `controller.devfile.io/mount-to-devworkspace: "true"`, which tells Dev Spaces to auto-mount it as environment variables in all workspaces in that namespace — no changes to `devfile.yaml` required.

---

## Step 3 — Create a workspace

### Option A — From a Git repository URL (easiest)

If this repo is in Git, open Dev Spaces and paste the factory URL:

```
https://<devspaces-host>/api/v1/plugins/workspace:start?url=https://github.com/<your-org>/pi
```

Dev Spaces reads `devfile.yaml` from the root of the repo and provisions the workspace.

### Option B — From the Dev Spaces dashboard

1. Open the Dev Spaces dashboard
2. Click **Create Workspace**
3. Paste the Git repo URL that contains `devfile.yaml`
4. Click **Create & Open**

### Option C — Import the devfile directly

```bash
# Using the che-cli or oc Dev Spaces plugin
chectl workspace:start --devfile=devfile.yaml
```

---

## Using pi in the workspace

Once the workspace is open in VS Code:

1. Open a terminal (**Terminal → New Terminal** or `` Ctrl+` ``)
2. The working directory is `/projects` (your cloned repo)
3. Run pi:

```bash
pi
```

pi will start in interactive TUI mode. All sessions and settings are saved to `/home/user/.pi/agent` (backed by the `pi-agent-home` PVC — persists across workspace restarts).

The **Task** sidebar also exposes two pre-configured commands:
- **Start pi agent** — runs `pi` in `/projects`
- **Show pi help** — runs `pi --help`

---

## Persistent Storage

| Mount | Backed by | Contents |
|---|---|---|
| `/projects` | Dev Spaces workspace PVC | Cloned Git repository |
| `/home/user/.pi/agent` | `pi-agent-home` PVC (2 Gi) | pi sessions, settings, extensions, skills, themes |

The `pi-agent-home` volume is defined in `devfile.yaml` and provisioned automatically by Dev Spaces when the workspace starts.

---

## Customising the workspace

### Change the image

Update `components[0].container.image` in `devfile.yaml`.

### Add more tools

Extend `Containerfile-devspaces` — the base image `quay.io/redhat-cop/devspaces-base:latest` already includes: `git`, `curl`, `jq`, `vim`, `zsh`, `ripgrep`, `fd`, `bat`, `gh-cli`, `buildah`, `podman`, `skopeo`, `oc`, `kubectl`.

### Increase memory/CPU

Edit `memoryLimit` / `cpuLimit` in the `pi` component in `devfile.yaml`.

---

## Security notes

- Container runs as arbitrary UID assigned by OpenShift (non-root). The image pre-creates `/home/user/.pi/agent` owned `10001:0` with `chmod g=u`, so any UID in GID 0 can write to it.
- API keys are injected as environment variables from a Secret — never baked into the image.
- Dev Spaces provides OAuth proxy authentication in front of every workspace automatically.
