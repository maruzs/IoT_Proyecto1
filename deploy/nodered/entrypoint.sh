#!/bin/sh
# =============================================================================
# Node-RED entrypoint wrapper
# Copia la config baked-in (flows, creds, settings) a /data en el primer run,
# luego arranca Node-RED normalmente.
# =============================================================================

STAGING="/etc/nodered-staging"

if [ ! -f /data/.nodered-initialized ]; then
    echo "[entrypoint] First run — copying baked-in configuration to /data"
    cp "$STAGING/flows.json"            /data/flows.json
    cp "$STAGING/flows_cred.json"       /data/flows_cred.json
    cp "$STAGING/settings.js"           /data/settings.js
    touch /data/.nodered-initialized
    echo "[entrypoint] Done. Starting Node-RED..."
else
    echo "[entrypoint] Configuration already initialized — skipping copy"
fi

exec /usr/local/bin/docker-entrypoint.sh npm start
