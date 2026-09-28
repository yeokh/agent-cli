#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# devpi-server entrypoint
#
# Initializes devpi-server on first run, sets up indexes, uploads any
# pre-loaded packages, then starts in server or ttyd mode.
#
# Environment variables (all optional — see Containerfile for defaults):
#
#   DEVPI_SERVERDIR      devpi data directory          (default: /data/devpi-server)
#   DEVPI_HOST           bind host                     (default: 0.0.0.0)
#   DEVPI_PORT           devpi port                    (default: 3141)
#   DEVPI_USER           devpi admin user              (default: root)
#   DEVPI_PASSWORD       devpi admin password          (default: "")
#   DEVPI_INDEX          local staging index name      (default: local)
#   DEVPI_BASES          index bases                   (default: "" = air-gapped)
#                          set to "root/pypi" to proxy through PyPI mirror
#   DEVPI_UPSTREAM_URL   upstream PyPI mirror URL      (default: https://pypi.org/simple/)
#   DEVPI_MODE           server | ttyd                 (default: server)
#   PACKAGES_DIR         pre-loaded packages dir       (default: /packages)
#   DEVPI_CLIENTDIR      devpi-client config dir       (default: /tmp/devpi-client)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

DEVPI_SERVERDIR="${DEVPI_SERVERDIR:-/data/devpi-server}"
DEVPI_HOST="${DEVPI_HOST:-0.0.0.0}"
DEVPI_PORT="${DEVPI_PORT:-3141}"
DEVPI_USER="${DEVPI_USER:-root}"
DEVPI_PASSWORD="${DEVPI_PASSWORD:-}"
DEVPI_INDEX="${DEVPI_INDEX:-local}"
DEVPI_BASES="${DEVPI_BASES:-}"
DEVPI_UPSTREAM_URL="${DEVPI_UPSTREAM_URL:-https://pypi.org/simple/}"
DEVPI_MODE="${DEVPI_MODE:-server}"
PACKAGES_DIR="${PACKAGES_DIR:-/packages}"

# Keep devpi-client state in /tmp — always writable regardless of injected UID
export DEVPI_CLIENTDIR="${DEVPI_CLIENTDIR:-/tmp/devpi-client}"
mkdir -p "${DEVPI_CLIENTDIR}"

DEVPI_URL="http://localhost:${DEVPI_PORT}"
INDEX_PATH="${DEVPI_USER}/${DEVPI_INDEX}"

log() { printf '[devpi] %s %s\n' "$(date '+%H:%M:%S')" "$*"; }

# ── 1. Initialize devpi-server on first run ───────────────────────────────────
if [ ! -f "${DEVPI_SERVERDIR}/.serverversion" ]; then
    log "First run — initializing devpi-server at ${DEVPI_SERVERDIR} ..."
    devpi-server --init --serverdir "${DEVPI_SERVERDIR}"
fi

# ── 2. Start devpi-server in the background ───────────────────────────────────
log "Starting devpi-server on ${DEVPI_HOST}:${DEVPI_PORT} ..."
devpi-server \
    --host    "${DEVPI_HOST}" \
    --port    "${DEVPI_PORT}" \
    --serverdir "${DEVPI_SERVERDIR}" \
    --restrict-modify root \
    &
DEVPI_PID=$!

# Ensure the background server is killed if this script exits unexpectedly
trap 'kill "${DEVPI_PID}" 2>/dev/null || true' EXIT

# ── 3. Wait until devpi-server is accepting requests ─────────────────────────
log "Waiting for devpi-server to be ready ..."
WAIT=30
while [ "${WAIT}" -gt 0 ]; do
    if curl -sf "${DEVPI_URL}/" > /dev/null 2>&1; then
        log "devpi-server is ready."
        break
    fi
    WAIT=$((WAIT - 1))
    if [ "${WAIT}" -eq 0 ]; then
        log "ERROR: devpi-server did not become ready within 30 seconds."
        exit 1
    fi
    sleep 1
done

# ── 4. Set up devpi client and configure indexes ──────────────────────────────
devpi use "${DEVPI_URL}"
devpi login "${DEVPI_USER}" --password="${DEVPI_PASSWORD}"

# Optionally create an upstream PyPI mirror index (used as a fallback/proxy)
if [ -n "${DEVPI_BASES}" ] && printf '%s' "${DEVPI_BASES}" | grep -q "root/pypi"; then
    if ! devpi index root/pypi > /dev/null 2>&1; then
        log "Creating upstream mirror index root/pypi -> ${DEVPI_UPSTREAM_URL} ..."
        devpi index -c root/pypi \
            type=mirror \
            mirror_url="${DEVPI_UPSTREAM_URL}"
    else
        log "Mirror index root/pypi already exists."
    fi
fi

# Create the local staging index if it does not already exist
if ! devpi index "${INDEX_PATH}" > /dev/null 2>&1; then
    log "Creating local staging index ${INDEX_PATH} ..."
    if [ -n "${DEVPI_BASES}" ]; then
        devpi index -c "${INDEX_PATH}" \
            type=stage \
            bases="${DEVPI_BASES}" \
            volatile=True
    else
        # Air-gapped mode: no upstream bases
        devpi index -c "${INDEX_PATH}" \
            type=stage \
            volatile=True
    fi
else
    log "Local index ${INDEX_PATH} already exists."
fi

devpi use "${INDEX_PATH}"

# Configure pip for this session (enables bare `pip install` to use devpi)
devpi use --set-cfg 2>/dev/null || true

# ── 5. Upload pre-loaded packages ─────────────────────────────────────────────
upload_packages() {
    shopt -s nullglob
    local pkgs=("${PACKAGES_DIR}"/*.whl \
                "${PACKAGES_DIR}"/*.tar.gz \
                "${PACKAGES_DIR}"/*.zip)
    shopt -u nullglob

    if [ "${#pkgs[@]}" -eq 0 ]; then
        log "No packages found in ${PACKAGES_DIR} — skipping upload."
        return 0
    fi

    log "Uploading ${#pkgs[@]} package file(s) from ${PACKAGES_DIR} ..."

    # Primary: devpi upload (understands the current active index)
    if devpi upload --no-vcs "${pkgs[@]}" 2>/dev/null; then
        log "Package upload complete (devpi upload)."
        return 0
    fi

    # Fallback: twine (standard PyPI upload protocol)
    log "devpi upload encountered issues; trying twine ..."
    if twine upload \
            --repository-url "${DEVPI_URL}/${INDEX_PATH}/" \
            --username       "${DEVPI_USER}" \
            --password       "${DEVPI_PASSWORD:-}" \
            --skip-existing \
            "${pkgs[@]}" 2>/dev/null; then
        log "Package upload complete (twine)."
        return 0
    fi

    log "WARNING: Some packages may not have been uploaded."
    log "         You can upload them manually from the terminal:"
    log "           devpi use ${INDEX_PATH}"
    log "           devpi upload --no-vcs /packages/*.whl"
}

if [ -d "${PACKAGES_DIR}" ]; then
    upload_packages
fi

# ── 6. Print access information ───────────────────────────────────────────────
log ""
log "╔═══════════════════════════════════════════════════════════════╗"
log "║  devpi PyPI Server — Ready                                   ║"
log "╠═══════════════════════════════════════════════════════════════╣"
log "║  Index URL (for pip):                                        ║"
log "║    ${DEVPI_URL}/${INDEX_PATH}/+simple/"
log "║                                                               ║"
log "║  Admin Web UI:                                               ║"
log "║    ${DEVPI_URL}"
log "╠═══════════════════════════════════════════════════════════════╣"
log "║  pip configuration:                                          ║"
log "║    pip config set global.index-url \\                        ║"
log "║      ${DEVPI_URL}/${INDEX_PATH}/+simple/                     ║"
log "║    pip config set global.trusted-host localhost              ║"
log "╚═══════════════════════════════════════════════════════════════╝"
log ""

# ── 7. Run in selected mode ────────────────────────────────────────────────────
case "${DEVPI_MODE}" in
    server)
        log "Mode: server — devpi-server listening on port ${DEVPI_PORT}."
        # Remove EXIT trap (normal operation — let devpi run until stopped)
        trap - EXIT
        wait "${DEVPI_PID}"
        ;;
    ttyd)
        log "Mode: ttyd — launching web terminal on port 7681."
        log "       Access: http://<host>:7681"
        # Remove EXIT trap; devpi stays running as background process
        trap - EXIT
        exec ttyd --port 7681 --writable bash
        ;;
    *)
        log "ERROR: Unknown DEVPI_MODE='${DEVPI_MODE}'. Valid values: server | ttyd"
        exit 1
        ;;
esac
