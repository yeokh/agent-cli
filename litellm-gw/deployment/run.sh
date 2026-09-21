#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# run.sh — Start LiteLLM Gateway with rootless Podman
#
# Usage:
#   cp .env.example .env && vim .env   # fill in your API keys
#   chmod +x run.sh
#   ./run.sh              # start (or restart) the container
#   ./run.sh stop         # stop the container
#   ./run.sh logs         # follow logs
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

CONTAINER_NAME="litellm-gw"
IMAGE="ghcr.io/berriai/litellm-non_root:latest"
HOST_PORT=4000
CONTAINER_PORT=4000
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Sub-commands ─────────────────────────────────────────────────────────────
case "${1:-start}" in
  stop)
    echo "Stopping $CONTAINER_NAME..."
    podman stop "$CONTAINER_NAME" && podman rm "$CONTAINER_NAME"
    exit 0
    ;;
  logs)
    podman logs -f "$CONTAINER_NAME"
    exit 0
    ;;
  start) ;;  # fall through to startup logic
  *)
    echo "Usage: $0 [start|stop|logs]"
    exit 1
    ;;
esac

# ── Pre-flight checks ─────────────────────────────────────────────────────────
if [[ ! -f "$SCRIPT_DIR/.env" ]]; then
  echo "ERROR: .env not found in $SCRIPT_DIR"
  echo "       Run: cp .env.example .env && vim .env"
  exit 1
fi

if [[ ! -f "$SCRIPT_DIR/config.yaml" ]]; then
  echo "ERROR: config.yaml not found in $SCRIPT_DIR"
  exit 1
fi

TIKTOKEN_HOST_DIR="$(realpath -m "$SCRIPT_DIR/../tiktoken_cache")"
if [[ ! -d "$TIKTOKEN_HOST_DIR" ]]; then
  echo "WARNING: tiktoken cache not found at $TIKTOKEN_HOST_DIR"
  echo "         Run './download-tiktoken-cache.sh' once to pre-download tokenizer files."
  echo "         Continuing without cache — LiteLLM will fetch from CDN on first use."
  TIKTOKEN_MOUNT=""
else
  TIKTOKEN_MOUNT="-v ${TIKTOKEN_HOST_DIR}:/tmp/tiktoken_cache:ro,z"
fi

# ── Launch ─────────────────────────────────────────────────────────────────────
echo ""
echo "Tip: run './run.sh logs' to follow container output."
echo "Tip: run 'loginctl enable-linger $USER' to keep the container alive after logout."
echo ""
echo "Quick tests once gateway started:"
echo "  # List available models:"
echo "  curl http://localhost:${HOST_PORT}/v1/models \\"
echo "    -H 'Authorization: Bearer \$LITELLM_MASTER_KEY'"
echo ""
echo "  # Chat completion:"
echo "  curl http://localhost:${HOST_PORT}/v1/chat/completions \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -H 'Authorization: Bearer \$LITELLM_MASTER_KEY' \\"
echo "    -d '{\"model\":\"gpt-5-mini\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello!\"}]}'"
echo ""
echo "Starting LiteLLM Gateway..."

# shellcheck disable=SC2086
podman run -it --rm \
  --name "$CONTAINER_NAME" \
  --replace \
  -p "${HOST_PORT}:${CONTAINER_PORT}" \
  --env-file "$SCRIPT_DIR/.env" \
  -v "$SCRIPT_DIR/config.yaml:/app/config.yaml:ro,z" \
  ${TIKTOKEN_MOUNT} \
  "$IMAGE" \
  --config /app/config.yaml --port "$CONTAINER_PORT"

echo ""
echo "✓  LiteLLM Gateway running → http://localhost:${HOST_PORT}"
echo ""
