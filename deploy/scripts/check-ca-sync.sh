#!/usr/bin/env bash
# =============================================================================
# check-ca-sync.sh — Verificar si el CA cert del ESP32-CAM está sincronizado
# =============================================================================
# Compara la huella SHA256 del CA cert en el broker Mosquitto contra la
# embebida en el firmware del ESP32-CAM. Si no coinciden, la ESP32-CAM
# no podrá conectarse vía TLS.
#
# Uso:
#   ./deploy/scripts/check-ca-sync.sh
#
# Salida:
#   exit 0 → CA sincronizado (no se requiere acción)
#   exit 1 → CA desincronizado (reflashear ESP32-CAM)
#   exit 2 → No se pudo leer alguno de los certificados
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DEPLOY_DIR="${PROJECT_ROOT}/deploy"
FIRMWARE_DIR="${PROJECT_ROOT}/src/esp32cam_firmware/src"
CA_FILE="${DEPLOY_DIR}/mosquitto/certs/ca.crt"
SECRETS_FILE="${FIRMWARE_DIR}/secrets.h"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🔐 Verificando sincronización CA cert — ESP32-CAM"
echo "=================================================="

# ── 1. Leer CA del broker ──
if [ ! -f "${CA_FILE}" ]; then
    echo -e "${RED}❌ ERROR:${NC} CA cert no encontrado en ${CA_FILE}"
    echo "   Ejecutá primero: cd deploy && docker compose up -d"
    exit 2
fi

BROKER_FINGERPRINT=$(openssl x509 -in "${CA_FILE}" -fingerprint -sha256 -noout 2>/dev/null | cut -d= -f2 | tr -d ' ')
if [ -z "${BROKER_FINGERPRINT}" ]; then
    echo -e "${RED}❌ ERROR:${NC} No se pudo leer la huella del CA cert del broker"
    exit 2
fi

echo "   Broker Mosquitto: ${BROKER_FINGERPRINT}"

# ── 2. Leer CA del firmware ESP32-CAM ──
if [ ! -f "${SECRETS_FILE}" ]; then
    echo -e "${YELLOW}⚠️  ATENCIÓN:${NC} secrets.h no encontrado en ${SECRETS_FILE}"
    echo "   Copiá el template primero: cp src/esp32cam_firmware/src/secrets.h.example src/esp32cam_firmware/src/secrets.h"
    exit 2
fi

# Extraer el certificado del secrets.h (formato: const char CA_CERT[] = R"EOF(\n...\n)EOF")
CA_CERT_CONTENT=$(sed -n '/CA_CERT\[\] = R"EOF(/,/)EOF"/p' "${SECRETS_FILE}" 2>/dev/null | \
    sed '1d;$d' | sed '/^$/d')

if [ -z "${CA_CERT_CONTENT}" ]; then
    echo -e "${YELLOW}⚠️  ATENCIÓN:${NC} No se encontró CA_CERT en secrets.h"
    echo "   ¿El firmware tiene el CA cert embebido? Ejecutá sync-ca-to-firmware.sh"
    exit 2
fi

FIRMWARE_FINGERPRINT=$(echo "${CA_CERT_CONTENT}" | openssl x509 -fingerprint -sha256 -noout 2>/dev/null | cut -d= -f2 | tr -d ' ')
if [ -z "${FIRMWARE_FINGERPRINT}" ]; then
    echo -e "${RED}❌ ERROR:${NC} No se pudo leer la huella del CA cert del firmware"
    exit 2
fi

echo "   Firmware ESP32-CAM: ${FIRMWARE_FINGERPRINT}"

# ── 3. Comparar ──
echo ""
if [ "${BROKER_FINGERPRINT}" = "${FIRMWARE_FINGERPRINT}" ]; then
    echo -e "${GREEN}✅ CA SINCRONIZADO${NC}"
    echo ""
    echo "   El CA cert del firmware ESP32-CAM coincide con el del broker."
    echo "   No es necesario reflashear."
    exit 0
else
    echo -e "${RED}❌ CA DESINCRONIZADO${NC}"
    echo ""
    echo "   El CA cert cambió. La ESP32-CAM NO podrá conectarse vía TLS."
    echo ""
    echo "   Para corregirlo:"
    echo "   1. ./deploy/scripts/sync-ca-to-firmware.sh"
    echo "   2. Reflashear la ESP32-CAM:"
    echo "      arduino-cli upload -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32cam src/esp32cam_firmware/"
    exit 1
fi
