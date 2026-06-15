#!/usr/bin/env bash
# =============================================================================
# flash.sh — Flashea MKR1000 y ESP32-CAM automáticamente
# =============================================================================
# Detecta placas conectadas, compila (con build-firmware.sh si es necesario)
# y flashea cada placa con su firmware correspondiente.
#
# Uso:
#   bash deploy/boards/flash.sh           # compila + flashea
#   bash deploy/boards/flash.sh --no-compile   # solo flashea (usa binarios pre-compilados)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

NO_COMPILE=false
if [ "${1:-}" = "--no-compile" ]; then
    NO_COMPILE=true
fi

green()  { echo -e "\033[32m$1\033[0m"; }
red()    { echo -e "\033[31m$1\033[0m"; }
yellow() { echo -e "\033[33m$1\033[0m"; }

# ---------------------------------------------------------------------------
# Compilar si es necesario
# ---------------------------------------------------------------------------
if [ "$NO_COMPILE" = false ]; then
    echo "[1/3] Compilando firmware..."
    bash "${SCRIPT_DIR}/build-firmware.sh"
else
    echo "[1/3] Omitiendo compilación (--no-compile)"
fi

# ---------------------------------------------------------------------------
# Detectar placas
# ---------------------------------------------------------------------------
echo ""
echo "[2/3] Detectando placas..."
BOARDS=$(arduino-cli board list --format json 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
for p in data.get('detected_ports', []):
    port = p['port']['address']
    boards = p.get('matching_boards', [])
    if boards:
        for b in boards:
            print(f\"{port}|{b['fqbn']}|{b['name']}\")
    else:
        # Placa no identificada por arduino-cli, intentar como ESP32
        print(f\"{port}|unknown|unknown\")
" 2>/dev/null || echo "")

if [ -z "$BOARDS" ]; then
    red "  ❌ No se detectaron placas conectadas"
    exit 1
fi

# ---------------------------------------------------------------------------
# Flashear cada placa
# ---------------------------------------------------------------------------
echo "[3/3] Flasheando..."
FLASHED=0

while IFS='|' read -r port fqbn name; do
    echo ""
    echo "  Placa: ${name} en ${port}"

    if echo "$fqbn" | grep -q "samd:mkr1000"; then
        echo "  → Firmware: MKR1000"
        arduino-cli upload -p "$port" --fqbn "$fqbn" "${PROJECT_ROOT}/src/mkr1000_firmware/" 2>&1 | tail -3
        FLASHED=$((FLASHED + 1))

    elif echo "$fqbn" | grep -q "esp32.*cam"; then
        echo "  → Firmware: ESP32-CAM"
        arduino-cli upload -p "$port" --fqbn "$fqbn" "${PROJECT_ROOT}/src/esp32cam_firmware/" 2>&1 | tail -3
        FLASHED=$((FLASHED + 1))

    elif echo "$fqbn" | grep -q "esp32"; then
        yellow "  → ESP32 genérico detectado. Probando ESP32-CAM..."
        arduino-cli upload -p "$port" --fqbn esp32:esp32:esp32cam "${PROJECT_ROOT}/src/esp32cam_firmware/" 2>&1 | tail -3
        FLASHED=$((FLASHED + 1))

    else
        yellow "  → Placa no reconocida (${fqbn}). Omitiendo."
    fi

done <<< "$BOARDS"

echo ""
echo "============================================================"
green " ${FLASHED} placa(s) flasheada(s)"
echo "============================================================"
