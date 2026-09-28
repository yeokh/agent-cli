#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# S4 entrypoint
#
# Creates the S3 admin user in the Ceph RGW SQLite database on first run,
# then hands off to supervisord which manages both the RGW daemon and the
# Node.js web server.
#
# Environment variables (all optional — see Containerfile for defaults):
#
#   AWS_ACCESS_KEY_ID      S3 admin access key ID          (default: s4admin)
#   AWS_SECRET_ACCESS_KEY  S3 admin secret access key      (default: s4secret)
#   S4_ADMIN_DISPLAY_NAME  Display name for the admin user (default: S4 Admin)
#   RGW_DATA_DIR           Ceph RGW data directory         (default: /var/lib/ceph/radosgw)
#
#   UI_USERNAME            Web UI login username (empty = no auth)
#   UI_PASSWORD            Web UI login password (empty = no auth)
#   PORT                   Node.js listen port             (default: 5000)
# ─────────────────────────────────────────────────────────────────────────────
set -e

AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-s4admin}"
AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-s4secret}"
S4_ADMIN_DISPLAY_NAME="${S4_ADMIN_DISPLAY_NAME:-S4 Admin}"
RGW_DATA_DIR="${RGW_DATA_DIR:-/var/lib/ceph/radosgw}"
PORT="${PORT:-5000}"

log() { printf '[s4] %s %s\n' "$(date '+%H:%M:%S')" "$*"; }

# ── 1. Ensure Ceph RGW data directories exist ─────────────────────────────────
#    A PVC mount may shadow the directories created at image build time.
log "Ensuring RGW data directories ..."
mkdir -p \
    "${RGW_DATA_DIR}/db" \
    "${RGW_DATA_DIR}/db/rgw_posix_lmdbs" \
    "${RGW_DATA_DIR}/buckets" \
    "${RGW_DATA_DIR}/tmp"

# ── 2. Create initial S3 admin user on first run ──────────────────────────────
#    radosgw-admin (with the dbstore backend) can write directly to the SQLite
#    database without the RGW HTTP daemon running. The command is idempotent —
#    subsequent runs fail silently via '|| true'.
LMDB_DIR="${RGW_DATA_DIR}/db/rgw_posix_lmdbs"
if [ -z "$(ls -A "${LMDB_DIR}" 2>/dev/null)" ]; then
    log "First run — creating S3 admin user '${AWS_ACCESS_KEY_ID}' ..."
    radosgw-admin user create \
        --uid      s4admin \
        --display-name "${S4_ADMIN_DISPLAY_NAME}" \
        --access-key   "${AWS_ACCESS_KEY_ID}" \
        --secret-key   "${AWS_SECRET_ACCESS_KEY}" \
        2>/dev/null || true
    log "S3 admin user created."
else
    log "Existing data found — skipping user creation."
fi

# ── 3. Print access information ───────────────────────────────────────────────
log ""
log "╔═══════════════════════════════════════════════════════════════╗"
log "║  S4 — Super Simple Storage Service — Starting               ║"
log "╠═══════════════════════════════════════════════════════════════╣"
log "║  Web UI:                                                     ║"
log "║    http://localhost:${PORT}/"
if [ -n "${UI_USERNAME}" ]; then
log "║    Login: ${UI_USERNAME}  /  <password from UI_PASSWORD>"
else
log "║    (no authentication required)"
fi
log "║                                                               ║"
log "║  S3 API:                                                     ║"
log "║    http://localhost:7480"
log "║    AWS_ACCESS_KEY_ID:     ${AWS_ACCESS_KEY_ID}"
log "║    AWS_SECRET_ACCESS_KEY: <value from AWS_SECRET_ACCESS_KEY>"
log "║                                                               ║"
log "║  Quick S3 test:                                              ║"
log "║    export AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}"
log "║    export AWS_SECRET_ACCESS_KEY=<secret>"
log "║    export AWS_ENDPOINT_URL=http://localhost:7480"
log "║    aws s3 mb s3://my-bucket"
log "╚═══════════════════════════════════════════════════════════════╝"
log ""

# ── 4. Start supervisord (manages radosgw + nodejs) ──────────────────────────
log "Starting supervisord ..."
exec /usr/local/bin/supervisord -c /etc/supervisord.conf
