#!/usr/bin/env bash
# Run opencode-cli locally with podman using named volumes.
#
# Usage:
#   ANTHROPIC_API_KEY=sk-ant-... ./podman-run.sh
#   ./podman-run.sh run "explain this repo"     # non-interactive
#   ./podman-run.sh auth login                  # one-time provider setup
#
# Override IMAGE or volume names by exporting the variables before running.
set -euo pipefail

IMAGE="${IMAGE:-opencode-cli:latest}"

# ── LLM provider API keys (optional; you can also use `auth login`) ─────────
ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
OPENAI_API_KEY="${OPENAI_API_KEY:-}"
GOOGLE_AI_API_KEY="${GOOGLE_AI_API_KEY:-}"

# ── Named volume names ───────────────────────────────────────────────────────
VOL_CONFIG="${VOL_CONFIG:-opencode-config}"
VOL_DATA="${VOL_DATA:-opencode-data}"
VOL_WORKSPACE="${VOL_WORKSPACE:-opencode-workspace}"

for vol in "${VOL_CONFIG}" "${VOL_DATA}" "${VOL_WORKSPACE}"; do
    podman volume inspect "${vol}" &>/dev/null || podman volume create "${vol}"
done

echo "  config    : podman volume ${VOL_CONFIG}" >&2
echo "  data      : podman volume ${VOL_DATA}" >&2
echo "  workspace : podman volume ${VOL_WORKSPACE}" >&2

exec podman run --rm -it \
    -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}" \
    -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
    -e GOOGLE_AI_API_KEY="${GOOGLE_AI_API_KEY}" \
    -v "${VOL_CONFIG}:/home/opencode/.config/opencode:Z" \
    -v "${VOL_DATA}:/home/opencode/.local/share/opencode:Z" \
    -v "${VOL_WORKSPACE}:/workspace:Z" \
    "${IMAGE}" "$@"
