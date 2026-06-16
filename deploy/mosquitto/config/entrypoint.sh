#!/usr/bin/env sh
# =============================================================================
# entrypoint.sh — Mosquitto startup validator
# =============================================================================
# Validates that all required TLS certificates and the password file exist
# before starting the Mosquitto broker.
#
# If any file is missing, exits with code 1 and prints an error message
# referencing generate-certs.sh.
# =============================================================================

CERT_DIR="/mosquitto/certs"
PASSWD_FILE="/mosquitto/config/passwd"

missing=0

for file in "${CERT_DIR}/ca.crt" "${CERT_DIR}/ca.key" "${CERT_DIR}/server.crt" "${CERT_DIR}/server.key" "${PASSWD_FILE}"; do
    if [ ! -f "$file" ]; then
        echo "ERROR: Required file missing: $file"
        missing=1
    fi
done

if [ "$missing" -ne 0 ]; then
    echo ""
    echo "TLS certificates or password file are missing."
    echo "Please run ./deploy/scripts/generate-certs.sh first:"
    echo ""
    echo "  export MQTT_USER=iot_user"
    echo "  export MQTT_PASSWORD=change_me_before_deploy"
    echo "  ./deploy/scripts/generate-certs.sh"
    echo ""
    exit 1
fi

# All files present — start Mosquitto
exec mosquitto -c /mosquitto/config/mosquitto.conf
