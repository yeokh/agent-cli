# opencode-cli container

Runs [opencode](https://opencode.ai) as an interactive TUI/CLI (default
`opencode` command, plus `run`, `auth`, `session`, etc.) inside a UBI 9
Minimal container. For the browser-based server variant, see
`../opencode-web/`.

---

## Directory layout

```
opencode/opencode-cli/
├── Containerfile     # Image build definition
├── entrypoint.sh     # Container startup script
├── podman-run.sh     # Local podman helper
└── README.md
```

---

## Why 3 volumes

| Volume | Mount path | Purpose |
|---|---|---|
| **Config** | `/home/opencode/.config/opencode` | Portable, versionable settings: `opencode.json`, `tui.json`, `agents/`, `commands/`, `plugins/`. Safe to back up or sync across machines. |
| **Data** | `/home/opencode/.local/share/opencode` | Persistent state: `auth.json` (provider credentials), the sessions DB, snapshots, logs. Sensitive — don't commit or share. |
| **Workspace** | `/workspace` | Your project source. Kept separate from the two dirs above so infrastructure (config/state) and code never mix. |

`~/.cache/opencode` (downloaded model list, LSP/formatter binaries) is left
un-mounted — it's disposable and gets rebuilt on first use, no need to
persist it.

---

## Build

```bash
podman build -t opencode-cli:latest -f Containerfile .
```

---

## Run locally with podman

The helper script creates the named volumes and runs the container:

```bash
ANTHROPIC_API_KEY=sk-ant-... ./podman-run.sh
```

Or do it by hand:

```bash
podman volume create opencode-config
podman volume create opencode-data
podman volume create opencode-workspace

podman run --rm -it \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -v opencode-config:/home/opencode/.config/opencode:Z \
  -v opencode-data:/home/opencode/.local/share/opencode:Z \
  -v opencode-workspace:/workspace:Z \
  opencode-cli:latest
```

### One-time provider setup

Instead of (or in addition to) env vars, log in interactively — credentials
are written to the data volume and persist across container restarts:

```bash
podman run --rm -it \
  -v opencode-config:/home/opencode/.config/opencode:Z \
  -v opencode-data:/home/opencode/.local/share/opencode:Z \
  opencode-cli:latest auth login
```

### Non-interactive `run`

```bash
podman run --rm \
  -v opencode-config:/home/opencode/.config/opencode:Z \
  -v opencode-data:/home/opencode/.local/share/opencode:Z \
  -v opencode-workspace:/workspace:Z \
  opencode-cli:latest run "explain this repo"
```

### Mount a host project instead of the workspace volume

```bash
podman run --rm -it \
  -v opencode-config:/home/opencode/.config/opencode:Z \
  -v opencode-data:/home/opencode/.local/share/opencode:Z \
  -v "$PWD:/workspace:Z" \
  opencode-cli:latest
```

### Shell access / debugging

```bash
podman run --rm -it \
  -v opencode-config:/home/opencode/.config/opencode:Z \
  -v opencode-data:/home/opencode/.local/share/opencode:Z \
  -v opencode-workspace:/workspace:Z \
  opencode-cli:latest bash
```

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `OPENCODE_DISABLE_AUTOUPDATE` | `true` | Prevent in-container self-update; rebuild the image to upgrade instead |
| `ANTHROPIC_API_KEY` | *(empty)* | Anthropic API key |
| `OPENAI_API_KEY` | *(empty)* | OpenAI API key |
| `GOOGLE_AI_API_KEY` | *(empty)* | Google AI API key |

Any other [opencode env var](https://opencode.ai/docs/cli/#environment-variables)
(`OPENCODE_CONFIG`, `OPENCODE_PERMISSION`, etc.) can be passed through with
`-e`.

---

## Notes

- Runs as UID 1001, group 0, with `g=u` permissions on `/home/opencode` and
  `/workspace` — works both for plain `podman run` and for OpenShift's
  arbitrary-UID SCCs.
- `git config --system --add safe.directory '*'` is set at build time so
  mounting a host directory (different uid/gid) into `/workspace` doesn't
  trigger git's "dubious ownership" error.
- To upgrade opencode, rebuild the image (`podman build --no-cache`) — the
  binary is baked in, not downloaded at runtime.
