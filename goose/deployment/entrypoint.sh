#!/usr/bin/env bash
set -euo pipefail

# OpenShift runs containers as an arbitrary UID; ensure writable dirs exist.
export HOME="${HOME:-/home/goose}"
mkdir -p "${HOME}/.config/goose/custom_providers" "${HOME}/workspace" 2>/dev/null || true

# Containers lack a usable system keyring; use file-based secrets instead.
export GOOSE_DISABLE_KEYRING="${GOOSE_DISABLE_KEYRING:-1}"

if [[ $# -eq 0 ]]; then
  exec goose
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
    exec goose "$@"
    ;;
esac
