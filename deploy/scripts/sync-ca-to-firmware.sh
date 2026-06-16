#!/usr/bin/env bash
# =============================================================================
# sync-ca-to-firmware.sh — Extrae el CA cert del volumen Docker y actualiza
#                          el secrets.h del ESP32-CAM para TLS.
# =============================================================================
# Uso:
#   ./deploy/scripts/sync-ca-to-firmware.sh
#
# Requiere:
#   - Mosquitto corriendo (docker compose up -d mosquitto)
#   - Volumen deploy_mosquitto_certs con ca.crt
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SECRETS_FILE="${PROJECT_ROOT}/src/esp32cam_firmware/src/secrets.h"
SECRETS_EXAMPLE="${PROJECT_ROOT}/src/esp32cam_firmware/src/secrets.h.example"
CERTS_VOLUME="deploy_mosquitto_certs"

echo "🔐 Sincronizando CA cert → ESP32-CAM secrets.h"

# 1. Extraer CA cert del volumen Docker
CA_CERT=$(docker run --rm -v "${CERTS_VOLUME}:/certs:ro" alpine:3 cat /certs/ca.crt 2>/dev/null)
if [ -z "$CA_CERT" ]; then
    echo "❌ ERROR: No se pudo leer el CA cert del volumen '${CERTS_VOLUME}'."
    echo "   ¿Está corriendo Mosquitto? Ejecutá: cd deploy && docker compose up -d mosquitto"
    exit 1
fi

# 2. Formatear para C++ (agregar comillas y saltos de línea)
CERT_LINES=""
while IFS= read -r line; do
    CERT_LINES="${CERT_LINES}${line}\n"
done <<< "$CA_CERT"
# Quitar última \n
CERT_LINES="${CERT_LINES%\\n}"

# 3. Leer el .example como base si secrets.h no existe
if [ ! -f "$SECRETS_FILE" ]; then
    if [ -f "$SECRETS_EXAMPLE" ]; then
        cp "$SECRETS_EXAMPLE" "$SECRETS_FILE"
        echo "   📄 secrets.h creado desde .example"
    else
        echo "❌ ERROR: No existe ${SECRETS_EXAMPLE}"
        exit 1
    fi
fi

# 4. Reemplazar el bloque CA_CERT en secrets.h con el certificado actual
#    Busca desde "const char CA_CERT[]" hasta ";)EOF\";" y lo reemplaza
CERT_BLOCK=$(cat <<HEREDOC
const char CA_CERT[] = R"EOF(
${CA_CERT}
)EOF";
HEREDOC
)

# Usar python para reemplazo multilínea seguro
python3 << PYEOF
import re

with open("${SECRETS_FILE}", "r") as f:
    content = f.read()

# Reemplazar bloque CA_CERT existente
new_content = re.sub(
    r'const char CA_CERT\[\] = R"EOF\(\).*?\)EOF";',
    r"""${CERT_BLOCK//$'\n'/\\n}""",
    content,
    flags=re.DOTALL
)

with open("${SECRETS_FILE}", "w") as f:
    f.write(new_content)
PYEOF

echo "✅ secrets.h actualizado con CA cert:"
openssl x509 -in <(echo "$CA_CERT") -noout -fingerprint -sha256 2>/dev/null || echo "   (fingerprint no disponible)"
echo ""
echo "⚠️  RECORDÁ: después de ejecutar este script, re-flashea la ESP32-CAM:"
echo "   arduino-cli upload -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32cam src/esp32cam_firmware/"
