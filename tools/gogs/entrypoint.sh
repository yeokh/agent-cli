#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Gogs entrypoint
#
# Initializes Gogs on first run (config + SQLite DB + admin user),
# then starts the server.
#
# Environment variables (all optional — see Containerfile for defaults):
#
#   GOGS_HTTP_PORT       HTTP listen port              (default: 3000)
#   GOGS_SSH_PORT        Built-in SSH listen port      (default: 2222)
#   GOGS_DOMAIN          External hostname / domain    (default: localhost)
#   GOGS_ADMIN_USER      Initial admin username        (default: gogs)
#   GOGS_ADMIN_PASSWORD  Initial admin password        (default: "" — prompts wizard)
#   GOGS_ADMIN_EMAIL     Initial admin e-mail          (default: gogs@localhost)
#   GOGS_CUSTOM          Custom config/data root       (default: /data/gogs)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

GOGS_HTTP_PORT="${GOGS_HTTP_PORT:-3000}"
GOGS_SSH_PORT="${GOGS_SSH_PORT:-2222}"
GOGS_DOMAIN="${GOGS_DOMAIN:-localhost}"
GOGS_ADMIN_USER="${GOGS_ADMIN_USER:-gogs}"
GOGS_ADMIN_PASSWORD="${GOGS_ADMIN_PASSWORD:-}"
GOGS_ADMIN_EMAIL="${GOGS_ADMIN_EMAIL:-gogs@localhost}"
GOGS_CUSTOM="${GOGS_CUSTOM:-/data/gogs}"

GOGS_BIN="/app/gogs/gogs"
CONF="${GOGS_CUSTOM}/conf/app.ini"
GOGS_URL="http://localhost:${GOGS_HTTP_PORT}"

log() { printf '[gogs] %s %s\n' "$(date '+%H:%M:%S')" "$*"; }

# ── 0. OpenShift arbitrary-UID support ───────────────────────────────────────
#    OpenShift injects a random UID that may not exist in /etc/passwd.
#    Go's os/user package (used by Gogs) needs a passwd entry to resolve the
#    current user; we register the injected UID under the "git" identity.
if ! whoami &>/dev/null; then
    if [ -w /etc/passwd ]; then
        log "Registering runtime UID $(id -u) in /etc/passwd (OpenShift arbitrary-UID mode) ..."
        echo "git:x:$(id -u):0:Gogs Git User:/home/git:/bin/bash" >> /etc/passwd
    fi
fi

# ── 1. Ensure data directories exist ─────────────────────────────────────────
log "Ensuring data directories ..."
for d in "${GOGS_CUSTOM}/data" \
          "${GOGS_CUSTOM}/conf" \
          "${GOGS_CUSTOM}/log" \
          /data/git/repositories \
          /data/ssh; do
    mkdir -p "$d"
done

# ── 2. Create app.ini on first run ────────────────────────────────────────────
#
#    Two modes depending on whether GOGS_ADMIN_PASSWORD is set:
#
#    Auto mode   (GOGS_ADMIN_PASSWORD non-empty):
#      Writes app.ini with INSTALL_LOCK=true and creates the admin account
#      via the Gogs CLI before starting the server. No web wizard required.
#
#    Wizard mode (GOGS_ADMIN_PASSWORD empty — default):
#      Writes app.ini with INSTALL_LOCK=false and server / DB defaults
#      pre-filled. On first visit the web installer shows with those defaults;
#      you only need to fill in the admin credentials.
if [ ! -f "${CONF}" ]; then
    log "First run — creating configuration at ${CONF} ..."

    INSTALL_LOCK="false"
    [ -n "${GOGS_ADMIN_PASSWORD}" ] && INSTALL_LOCK="true"

    # Generate a random secret key (used for cookies / CSRF tokens)
    SECRET_KEY=$(cat /proc/sys/kernel/random/uuid 2>/dev/null | tr -d '-' \
                 || printf '%s' "$(date +%s%N)" | sha256sum | head -c 32)

    cat > "${CONF}" << EOF
RUN_MODE = prod

[database]
DB_TYPE  = sqlite3
PATH     = /data/gogs/data/gogs.db

[repository]
ROOT = /data/git/repositories

[server]
HTTP_ADDR        = 0.0.0.0
HTTP_PORT        = ${GOGS_HTTP_PORT}
DOMAIN           = ${GOGS_DOMAIN}
ROOT_URL         = http://${GOGS_DOMAIN}:${GOGS_HTTP_PORT}/
START_SSH_SERVER = true
SSH_LISTEN_HOST  = 0.0.0.0
SSH_PORT         = ${GOGS_SSH_PORT}

[mailer]
ENABLED = false

[service]
REGISTER_EMAIL_CONFIRM = false
ENABLE_NOTIFY_MAIL     = false
DISABLE_REGISTRATION   = false
ENABLE_CAPTCHA         = false
REQUIRE_SIGNIN_VIEW    = false

[picture]
DISABLE_GRAVATAR = true

[session]
PROVIDER        = file
PROVIDER_CONFIG = /data/gogs/data/sessions

[log]
MODE      = console, file
LEVEL     = Info
ROOT_PATH = ${GOGS_CUSTOM}/log

[security]
INSTALL_LOCK = ${INSTALL_LOCK}
SECRET_KEY   = ${SECRET_KEY}
EOF

    log "Configuration created (INSTALL_LOCK=${INSTALL_LOCK})."
fi

# ── 3. Auto-provision admin user on first run ─────────────────────────────────
#    Only runs when GOGS_ADMIN_PASSWORD is set and no DB exists yet.
if [ -n "${GOGS_ADMIN_PASSWORD}" ] && [ ! -f "/data/gogs/data/gogs.db" ]; then
    log "Auto mode — creating admin account '${GOGS_ADMIN_USER}' ..."
    if "${GOGS_BIN}" admin user create \
            --admin \
            --username="${GOGS_ADMIN_USER}" \
            --password="${GOGS_ADMIN_PASSWORD}" \
            --email="${GOGS_ADMIN_EMAIL}" 2>&1 | tee -a "${GOGS_CUSTOM}/log/init.log"; then
        log "Admin account created."
    else
        log "WARNING: Could not create admin account automatically."
        log "         Visit the web UI to complete setup."
    fi
fi

# ── 4. Print access information ───────────────────────────────────────────────
log ""
log "╔═══════════════════════════════════════════════════════════════╗"
log "║  Gogs Git Server — Starting                                  ║"
log "╠═══════════════════════════════════════════════════════════════╣"
log "║  Web UI:                                                     ║"
log "║    http://${GOGS_DOMAIN}:${GOGS_HTTP_PORT}/"
log "║                                                               ║"
log "║  Git over HTTP:                                              ║"
log "║    http://${GOGS_DOMAIN}:${GOGS_HTTP_PORT}/<user>/<repo>.git"
log "║                                                               ║"
log "║  Git over SSH (built-in server):                            ║"
log "║    ssh://git@${GOGS_DOMAIN}:${GOGS_SSH_PORT}/<user>/<repo>.git"
log "╠═══════════════════════════════════════════════════════════════╣"
if [ -n "${GOGS_ADMIN_PASSWORD}" ]; then
log "║  Admin:  ${GOGS_ADMIN_USER}  /  <password from GOGS_ADMIN_PASSWORD>"
else
log "║  First run: open the web UI to complete setup.              ║"
fi
log "╚═══════════════════════════════════════════════════════════════╝"
log ""

# ── 5. Start gogs ─────────────────────────────────────────────────────────────
log "Starting gogs web server ..."
exec "${GOGS_BIN}" web
