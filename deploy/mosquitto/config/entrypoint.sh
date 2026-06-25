#!/usr/bin/env sh
# =============================================================================
# entrypoint.sh — Mosquitto startup validator + runtime passwd generator
# =============================================================================
# 1. Validates that all required TLS certificates exist before starting the
#    Mosquitto broker.
# 2. Generates /mosquitto/config/passwd at runtime from the 7 per-client
#    MQTT_USER_* / MQTT_PASS_* environment variables.
# 3. Starts Mosquitto with the loaded configuration.
#
# If any certificate file is missing, exits with code 1 and prints an error
# message referencing generate-certs.sh.
# =============================================================================

set -e

CERT_DIR="/mosquitto/certs"
PASSWD_FILE="/mosquitto/config/passwd"

missing=0

for file in "${CERT_DIR}/ca.crt" "${CERT_DIR}/ca.key" "${CERT_DIR}/server.crt" "${CERT_DIR}/server.key"; do
    if [ ! -f "$file" ]; then
        echo "ERROR: Required file missing: $file"
        missing=1
    fi
done

if [ "$missing" -ne 0 ]; then
    echo ""
    echo "TLS certificates are missing."
    echo "Please run ./deploy/scripts/generate-certs.sh first:"
    echo ""
    echo "  ./deploy/scripts/generate-certs.sh"
    echo ""
    exit 1
fi

# ---------------------------------------------------------------------------
# Runtime passwd generation from per-client env vars (T-002 + T-005)
# ---------------------------------------------------------------------------
# Clear existing passwd file — credentials are regenerated on every start.
> "$PASSWD_FILE"

for user in MKR1000 ESP32CAM BACKEND NODERED LLMGATEWAY DIGITALTWIN COAPBRIDGE; do
    eval "username=\${MQTT_USER_$user}"
    eval "password=\${MQTT_PASS_$user}"

    if [ -n "$username" ] && [ -n "$password" ]; then
        mosquitto_passwd -b "$PASSWD_FILE" "$username" "$password"
    fi
done

# Fix passwd file permissions
chmod 0644 "$PASSWD_FILE"

# All files present — start Mosquitto
exec mosquitto -c /mosquitto/config/mosquitto.conf
