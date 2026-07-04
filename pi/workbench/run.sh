#!/usr/bin/env bash
set -euo pipefail

# ── OpenShift arbitrary-UID support ──────────────────────────────────────────
# OpenShift runs containers with a random UID that may not exist in /etc/passwd.
# Programs that call getpwuid() (including bash, ttyd) need a valid entry.
if ! whoami &>/dev/null; then
    if [ -w /etc/passwd ]; then
        echo "user:x:$(id -u):0:user:${HOME}:/bin/bash" >> /etc/passwd
    fi
fi

# ── Resolve NB_PREFIX ────────────────────────────────────────────────────────
# RHOAI sets NB_PREFIX to the sub-path the workbench is served from, e.g.:
#   /notebookserver/notebooks/default/my-pi
# When running standalone (no JupyterHub) default to /pi.
NB_PREFIX="${NB_PREFIX:-/pi}"
# Strip any trailing slash so templates stay consistent
NB_PREFIX="${NB_PREFIX%/}"
export NB_PREFIX

echo "Starting pi workbench with NB_PREFIX='${NB_PREFIX}'"

# ── Generate nginx server config from template ────────────────────────────────
mkdir -p /tmp/nginx-client-body /tmp/nginx-proxy /tmp/nginx-fastcgi \
         /tmp/nginx-uwsgi /tmp/nginx-scgi

envsubst '${NB_PREFIX}' \
    < /opt/app-root/etc/proxy.conf.template \
    > /tmp/nginx-server.conf

# ── Start nginx ───────────────────────────────────────────────────────────────
nginx -c /opt/app-root/etc/nginx.conf
echo "nginx started (port 8080)"

# ── Start ttyd serving pi ─────────────────────────────────────────────────────
# --base-path tells ttyd its URL prefix so its JS/WS references are correct
# --writable  allows keyboard input
# --once      is NOT set — allow multiple browser sessions
echo "Starting ttyd (port 7681, base-path=${NB_PREFIX}/)"
exec ttyd \
    --port 7681 \
    --base-path "${NB_PREFIX}/" \
    --writable \
    pi
