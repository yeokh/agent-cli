#!/usr/bin/env bash
# nanobot ttyd entrypoint
#
# Controls which command ttyd exposes via the browser terminal.
# Set NANOBOT_TTYD_CMD to one of:
#
#   agent  (default) — nanobot interactive TUI agent session
#   webui             — nanobot gateway + WebUI server (headless; access via port 8765 Route)
#   bash              — plain bash shell with nanobot on PATH
#
# Example (override at runtime):
#   -e NANOBOT_TTYD_CMD=bash
set -euo pipefail

case "${NANOBOT_TTYD_CMD:-agent}" in
  agent)
    exec ttyd --port 7681 --writable nanobot agent
    ;;
  webui)
    # Starts the nanobot gateway (18790) and WebUI server (8765).
    # --no-open: skip browser launch (headless container)
    # --yes:     apply safe defaults without interactive prompts
    # NOTE: expose and route ports 18790 and 8765 in addition to 7681
    #       if you want to access the WebUI directly.
    exec ttyd --port 7681 --writable \
        nanobot webui --no-open --yes
    ;;
  bash)
    exec ttyd --port 7681 --writable bash
    ;;
  *)
    echo "Unknown NANOBOT_TTYD_CMD='${NANOBOT_TTYD_CMD}'. Valid: agent | webui | bash" >&2
    exit 1
    ;;
esac
