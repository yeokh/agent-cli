#!/usr/bin/env bash
# Run opencode-web locally with podman using named volumes.
# Named volumes mirror the PVC-based approach used in OpenShift deployment.
#
# Usage:
#   ANTHROPIC_API_KEY=sk-ant-... OPENCODE_SERVER_PASSWORD=secret ./podman-run.sh
#
# Override IMAGE or volume names by exporting the variables before running.
set -euo pipefail

IMAGE="quay.io/kenghua_yeo/opencode-web:v1"

# ── Auth (place-holder for user/password) ───────────────────────────────────────
## OPENCODE_SERVER_USERNAME="${OPENCODE_SERVER_USERNAME:-opencode}"
## OPENCODE_SERVER_PASSWORD="${OPENCODE_SERVER_PASSWORD:-changeme}"

# ── LLM provider API keys ───────────────────────────────────────────────────────
ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
OPENAI_API_KEY="${OPENAI_API_KEY:-}"
GOOGLE_AI_API_KEY="${GOOGLE_AI_API_KEY:-}"

# ── Named volume names (mirrors PVC names in pvc.yaml) ──────────────────────────
VOL_WORKSPACE="${VOL_WORKSPACE:-opencode-workspace}"
VOL_CONFIG="${VOL_CONFIG:-opencode-config}"
VOL_DATA="${VOL_DATA:-opencode-data}"
VOL_AGENT="${VOL_AGENT:-opencode-agent}"
VOL_SKILLS="${VOL_SKILLS:-opencode-skills}"

# Create volumes if they don't exist yet
for vol in "${VOL_WORKSPACE}" "${VOL_CONFIG}" "${VOL_DATA}" "${VOL_AGENT}" "${VOL_SKILLS}"; do
    podman volume inspect "${vol}" &>/dev/null || podman volume create "${vol}"
done

# Optionally seed the agent / skills volumes from local paths on first run.
# Set SEED_AGENT_DIR / SEED_SKILLS_DIR to trigger a one-time rsync into the volume.
if [[ -n "${SEED_AGENT_DIR:-}" ]]; then
    echo "Seeding agent volume from ${SEED_AGENT_DIR} …"
    podman run --rm \
        -v "${SEED_AGENT_DIR}:/src:ro,Z" \
        -v "${VOL_AGENT}:/dst:Z" \
        registry.redhat.io/ubi9/nodejs-24-minimal \
        bash -c "cp -r /src/. /dst/"
fi

if [[ -n "${SEED_SKILLS_DIR:-}" ]]; then
    echo "Seeding skills volume from ${SEED_SKILLS_DIR} …"
    podman run --rm \
        -v "${SEED_SKILLS_DIR}:/src:ro,Z" \
        -v "${VOL_SKILLS}:/dst:Z" \
        registry.redhat.io/ubi9/nodejs-24-minimal \
        bash -c "cp -r /src/. /dst/"
fi

echo "Starting opencode-web on http://localhost:8081"
echo "  workspace : podman volume ${VOL_WORKSPACE}"
echo "  config    : podman volume ${VOL_CONFIG}"
echo "  data      : podman volume ${VOL_DATA}"
echo "  agent     : podman volume ${VOL_AGENT}  (read-only)"
echo "  skills    : podman volume ${VOL_SKILLS}  (read-only)"
echo "Use podman stop/kill opencode-web or podman ps and stop the container with podman stop <container-id>"

podman run --rm -d --name opencode-web -p 8081:8081 \
    -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}" \
    -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
    -e GOOGLE_AI_API_KEY="${GOOGLE_AI_API_KEY}" \
    -e OPENCODE_DISABLE_AUTOUPDATE=true \
    -e BROWSER=true \
    -v "${VOL_WORKSPACE}:/workspace:Z" \
    -v "${VOL_CONFIG}:/home/opencode/.config/opencode:Z" \
    -v "${VOL_DATA}:/home/opencode/.local/share/opencode:Z" \
    -v "${VOL_AGENT}:/home/opencode/.opencode/agent:ro,Z" \
    -v "${VOL_SKILLS}:/home/opencode/.cursor/skills-cursor:ro,Z" \
    "${IMAGE}"
