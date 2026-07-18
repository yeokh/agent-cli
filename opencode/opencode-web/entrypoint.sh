#!/usr/bin/env bash
set -euo pipefail

# ── Ensure writable dirs exist for arbitrary UIDs (OpenShift SCC) ─────────────
# When OpenShift assigns a random UID the directories may not pre-exist for
# that UID, but because they are group-0-writable (g=u) the mkdir succeeds.
mkdir -p \
    "${HOME}/.config/opencode" \
    "${HOME}/.local/share/opencode" \
    "${HOME}/.opencode/agent"

# ── Validate auth config ───────────────────────────────────────────────────────
# Simple user/password login with default OPENCODE_SERVER_USER=opencode
if [[ -z "${OPENCODE_SERVER_PASSWORD:-}" ]]; then
    echo "WARNING: OPENCODE_SERVER_PASSWORD is not set. The web UI will be unauthenticated." >&2
fi

# ── Build argument list ────────────────────────────────────────────────────────
ARGS=(
    web
    --port     "${OPENCODE_PORT:-8081}"
    --hostname "${OPENCODE_HOSTNAME:-0.0.0.0}"
)

if [[ -n "${OPENCODE_CORS:-}" ]]; then
    ARGS+=(--cors "${OPENCODE_CORS}")
fi

exec opencode "${ARGS[@]}"
