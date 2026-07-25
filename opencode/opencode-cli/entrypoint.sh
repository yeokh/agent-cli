#!/usr/bin/env bash
set -euo pipefail

# ── Ensure writable dirs exist for arbitrary UIDs (OpenShift SCC) ────────────
# When OpenShift assigns a random UID the directories may not pre-exist for
# that UID, but because they are group-0-writable (g=u) the mkdir succeeds.
mkdir -p \
    "${HOME}/.config/opencode" \
    "${HOME}/.local/share/opencode" \
    /workspace

if [[ $# -eq 0 ]]; then
    # No args: launch the interactive TUI (requires `podman run -it`).
    exec opencode
fi

case "$1" in
    bash|/bin/bash|sh)
        shift
        exec /bin/bash "$@"
        ;;
    sleep)
        shift
        exec sleep "$@"
        ;;
    *)
        exec opencode "$@"
        ;;
esac
