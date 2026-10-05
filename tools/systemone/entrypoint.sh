#!/usr/bin/env bash
set -euo pipefail

LISTEN_HOST="${LISTEN_HOST:-0.0.0.0}"
LISTEN_PORT="${LISTEN_PORT:-8009}"

echo "Starting System One gateway on ${LISTEN_HOST}:${LISTEN_PORT}"
echo "Upstream: ${UPSTREAM_BASE_URL:-https://openrouter.ai/api}"
echo "Default model: ${DEFAULT_MODEL:-jev-latest}"

exec python -m uvicorn app.main:app \
    --host "${LISTEN_HOST}" \
    --port "${LISTEN_PORT}"
