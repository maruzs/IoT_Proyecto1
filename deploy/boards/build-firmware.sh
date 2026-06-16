#!/usr/bin/env bash
# =============================================================================
# build-firmware.sh — Compila MKR1000 y ESP32-CAM con credenciales de .env
# =============================================================================
# Extrae la CA del build de Mosquitto, genera secrets.h dinámicamente,
# compila ambos firmwares y copia los binarios a deploy/boards/.
#
# Requisitos:
#   - docker compose build mosquitto (ejecutado previamente)
#   - arduino-cli instalado y configurado
#   - deploy/.env con WIFI_SSID, WIFI_PASSWORD, MQTT_USER, etc.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BOARDS_DIR="${SCRIPT_DIR}"
CERTS_DIR="${PROJECT_ROOT}/deploy/mosquitto/certs"
DEPLOY_DIR="${PROJECT_ROOT}/deploy"

# ---------------------------------------------------------------------------
# Cargar .env
# ---------------------------------------------------------------------------
if [ -f "${DEPLOY_DIR}/.env" ]; then
    set -a; source "${DEPLOY_DIR}/.env"; set +a
fi

WIFI_SSID="${WIFI_SSID:-AAAAA}"
WIFI_PASSWORD="${WIFI_PASSWORD:-ekisdeee}"
MQTT_BROKER_IP="${MQTT_BROKER_IP:-10.167.230.179}"
MQTT_PORT="${MQTT_PORT:-8883}"
MQTT_USER="${MQTT_USER:-equipo69}"
MQTT_PASSWORD="${MQTT_PASSWORD:-IoT2026Secure!}"

# ---------------------------------------------------------------------------
# Extraer CA cert
# ---------------------------------------------------------------------------
echo "[1/4] Extrayendo CA cert..."

CA_CERT=""
if [ -f "${CERTS_DIR}/ca.crt" ]; then
    # Si generate-certs.sh ya corrió, usamos el archivo local
    CA_CERT=$(cat "${CERTS_DIR}/ca.crt")
    echo "  ✅ CA cert leído de ${CERTS_DIR}/ca.crt"
elif docker compose -f "${DEPLOY_DIR}/docker-compose.yml" images mosquitto 2>/dev/null | grep -q mosquitto; then
    # Extraer de la imagen construida
    CA_CERT=$(docker compose -f "${DEPLOY_DIR}/docker-compose.yml" run --rm --entrypoint cat mosquitto /ca.crt 2>/dev/null || true)
    if [ -n "$CA_CERT" ]; then
        echo "  ✅ CA cert extraído de la imagen Mosquitto"
    fi
fi

if [ -z "$CA_CERT" ]; then
    echo "  ❌ No se encontró CA cert. Ejecutá primero:"
    echo "     docker compose -f ${DEPLOY_DIR}/docker-compose.yml build mosquitto"
    echo "     o"
    echo "     bash ${PROJECT_ROOT}/deploy/scripts/generate-certs.sh"
    exit 1
fi

# ---------------------------------------------------------------------------
# Generar secrets.h para MKR1000
# ---------------------------------------------------------------------------
echo "[2/4] Generando secrets.h para MKR1000..."

cat > "${PROJECT_ROOT}/src/mkr1000_firmware/src/secrets.h" << EOF
#ifndef MKR1000_SECRETS_H
#define MKR1000_SECRETS_H
#define WIFI_SSID     "${WIFI_SSID}"
#define WIFI_PASSWORD "${WIFI_PASSWORD}"
#define MQTT_SERVER   "${MQTT_BROKER_IP}"
#define MQTT_PORT     ${MQTT_PORT}
#define MQTT_USER     "${MQTT_USER}"
#define MQTT_PASSWORD "${MQTT_PASSWORD}"
const char CA_CERT[] = R"EOF(
${CA_CERT}
)EOF";
#endif
EOF
echo "  ✅ secrets.h generado"

# ---------------------------------------------------------------------------
# Generar secrets.h para ESP32-CAM
# ---------------------------------------------------------------------------
echo "[3/4] Generando secrets.h para ESP32-CAM..."

cat > "${PROJECT_ROOT}/src/esp32cam_firmware/src/secrets.h" << EOF
#ifndef ESP32CAM_SECRETS_H
#define ESP32CAM_SECRETS_H
#define WIFI_SSID     "${WIFI_SSID}"
#define WIFI_PASSWORD "${WIFI_PASSWORD}"
#define MQTT_SERVER   "${MQTT_BROKER_IP}"
#define MQTT_PORT     ${MQTT_PORT}
#define MQTT_USER     "${MQTT_USER}"
#define MQTT_PASSWORD "${MQTT_PASSWORD}"
const char CA_CERT[] = R"EOF(
${CA_CERT}
)EOF";
#endif
EOF
echo "  ✅ secrets.h generado"

# ---------------------------------------------------------------------------
# Compilar firmware
# ---------------------------------------------------------------------------
echo "[4/4] Compilando firmware..."

echo "  MKR1000..."
arduino-cli compile --fqbn arduino:samd:mkr1000 "${PROJECT_ROOT}/src/mkr1000_firmware/" 2>&1 | tail -3

echo "  ESP32-CAM..."
arduino-cli compile --fqbn esp32:esp32:esp32cam "${PROJECT_ROOT}/src/esp32cam_firmware/" 2>&1 | tail -3

# ---------------------------------------------------------------------------
# Copiar binarios a deploy/boards/
# ---------------------------------------------------------------------------
ARDUINO_TMP=$(arduino-cli compile --fqbn arduino:samd:mkr1000 --show-properties "${PROJECT_ROOT}/src/mkr1000_firmware/" 2>/dev/null | grep "^build.path=" | cut -d= -f2)
ESP32_TMP=$(arduino-cli compile --fqbn esp32:esp32:esp32cam --show-properties "${PROJECT_ROOT}/src/esp32cam_firmware/" 2>/dev/null | grep "^build.path=" | cut -d= -f2)

if [ -d "${ARDUINO_TMP}" ]; then
    cp "${ARDUINO_TMP}/"*.bin "${ARDUINO_TMP}/"*.hex "${BOARDS_DIR}/" 2>/dev/null || true
    echo "  ✅ Binarios MKR1000 copiados"
fi

if [ -d "${ESP32_TMP}" ]; then
    cp "${ESP32_TMP}/"*.bin "${BOARDS_DIR}/" 2>/dev/null || true
    echo "  ✅ Binarios ESP32-CAM copiados"
fi

# ---------------------------------------------------------------------------
# Limpiar secrets.h (contienen credenciales)
# ---------------------------------------------------------------------------
rm "${PROJECT_ROOT}/src/mkr1000_firmware/src/secrets.h"
rm "${PROJECT_ROOT}/src/esp32cam_firmware/src/secrets.h"

echo ""
echo "============================================================"
echo " Firmware compilado. Binarios en deploy/boards/"
echo " Para flashear:  bash deploy/boards/flash.sh"
echo "============================================================"
