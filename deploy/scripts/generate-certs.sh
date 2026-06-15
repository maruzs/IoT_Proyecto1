#!/usr/bin/env bash
# =============================================================================
# generate-certs.sh — Self-signed PKI + Mosquitto password file generator
# =============================================================================
# Usage:
#   export MQTT_USER=iot_user
#   export MQTT_PASSWORD=change_me_before_deploy
#   ./deploy/scripts/generate-certs.sh
#
# Outputs (idempotent — safe to re-run):
#   deploy/mosquitto/certs/ca.key       CA private key (RSA 2048)
#   deploy/mosquitto/certs/ca.crt       CA certificate (365 days)
#   deploy/mosquitto/certs/server.key   Server private key (RSA 2048)
#   deploy/mosquitto/certs/server.crt   Server certificate (365 days)
#   deploy/mosquitto/config/passwd      mosquitto_passwd file
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CERTS_DIR="${PROJECT_ROOT}/deploy/mosquitto/certs"
PASSWD_FILE="${PROJECT_ROOT}/deploy/mosquitto/config/passwd"

# ---------------------------------------------------------------------------
# Validate prerequisites
# ---------------------------------------------------------------------------
if ! command -v openssl &>/dev/null; then
    echo "ERROR: OpenSSL is not installed. Please install OpenSSL and try again."
    exit 1
fi

if [[ -z "${MQTT_USER:-}" || -z "${MQTT_PASSWORD:-}" ]]; then
    echo "ERROR: MQTT_USER and MQTT_PASSWORD environment variables must be set."
    echo "Example:"
    echo "  export MQTT_USER=iot_user"
    echo "  export MQTT_PASSWORD=change_me_before_deploy"
    exit 2
fi

# ---------------------------------------------------------------------------
# Create output directories
# ---------------------------------------------------------------------------
mkdir -p "${CERTS_DIR}"
mkdir -p "$(dirname "${PASSWD_FILE}")"

# ---------------------------------------------------------------------------
# Generate CA key and self-signed certificate
# ---------------------------------------------------------------------------
echo "[1/4] Generating CA key and certificate..."
openssl genrsa -out "${CERTS_DIR}/ca.key" 2048 2>/dev/null
openssl req -new -x509 -days 365 -key "${CERTS_DIR}/ca.key" \
    -out "${CERTS_DIR}/ca.crt" \
    -subj "/C=AR/O=SmartHomeIoT/CN=SmartHomeIoT-CA" 2>/dev/null

# ---------------------------------------------------------------------------
# Generate server key and certificate signed by CA
# ---------------------------------------------------------------------------
echo "[2/4] Generating server key and certificate..."
openssl genrsa -out "${CERTS_DIR}/server.key" 2048 2>/dev/null

openssl req -new -key "${CERTS_DIR}/server.key" \
    -out "${CERTS_DIR}/server.csr" \
    -subj "/C=AR/O=SmartHomeIoT/CN=mosquitto" 2>/dev/null

openssl x509 -req -in "${CERTS_DIR}/server.csr" \
    -CA "${CERTS_DIR}/ca.crt" -CAkey "${CERTS_DIR}/ca.key" \
    -CAcreateserial -out "${CERTS_DIR}/server.crt" -days 365 \
    -extfile <(printf "subjectAltName=DNS:mosquitto,DNS:localhost,IP:127.0.0.1") 2>/dev/null

# ---------------------------------------------------------------------------
# Clean up intermediate files
# ---------------------------------------------------------------------------
rm -f "${CERTS_DIR}/server.csr" "${CERTS_DIR}/ca.srl"

# ---------------------------------------------------------------------------
# Generate Mosquitto password file
# ---------------------------------------------------------------------------
echo "[3/4] Generating Mosquitto password file..."
rm -f "${PASSWD_FILE}"
if command -v mosquitto_passwd &>/dev/null; then
    mosquitto_passwd -b -c "${PASSWD_FILE}" "${MQTT_USER}" "${MQTT_PASSWORD}"
else
    echo "WARNING: mosquitto_passwd not found in PATH."
    echo "         Attempting to use Docker to generate the password file..."
    docker run --rm -v "$(dirname "${PASSWD_FILE}"):/work" \
        eclipse-mosquitto:2 \
        mosquitto_passwd -b -c /work/passwd "${MQTT_USER}" "${MQTT_PASSWORD}"
fi

# ---------------------------------------------------------------------------
# Verify outputs
# ---------------------------------------------------------------------------
echo "[4/4] Verifying certificates..."
openssl x509 -in "${CERTS_DIR}/ca.crt" -noout -subject -dates
openssl x509 -in "${CERTS_DIR}/server.crt" -noout -subject -dates -ext subjectAltName
openssl verify -CAfile "${CERTS_DIR}/ca.crt" "${CERTS_DIR}/server.crt" >/dev/null

echo ""
echo "============================================================"
echo "Certificate generation completed successfully!"
echo "============================================================"
echo ""
echo "Files generated:"
echo "  ${CERTS_DIR}/ca.crt"
echo "  ${CERTS_DIR}/ca.key"
echo "  ${CERTS_DIR}/server.crt"
echo "  ${CERTS_DIR}/server.key"
echo "  ${PASSWD_FILE}"
echo ""
echo "IMPORTANT: Keep ca.key and server.key secure. Do NOT commit them to git."
