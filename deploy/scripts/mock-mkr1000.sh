#!/usr/bin/env bash
# =============================================================================
# mock-mkr1000.sh — Publica datos falsos cada 2s como si fuera el MKR1000
# =============================================================================
# Útil para la presentación cuando la placa no conecta WiFi o no está
# disponible. Publica en el mismo tópico que el MKR1000 real, y todo el
# pipeline (Digital Twin → InfluxDB → Grafana → MCP → LangGraph) funciona
# idéntico.
#
# Uso:
#   bash deploy/scripts/mock-mkr1000.sh           # datos con variación realista
#   bash deploy/scripts/mock-mkr1000.sh --critico  # simula alarma de gas
#   bash deploy/scripts/mock-mkr1000.sh --calor    # simula temperatura alta
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CERTS="${PROJECT_ROOT}/deploy/mosquitto/certs/ca.crt"
BROKER="localhost"
PORT=8883
USER="mkr1000-equipo69"
PASS="test123"
EQUIPO="equipo69"

# Escenario por defecto: hogar normal
MODO="${1:-normal}"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           Mock MKR1000 — Publicando datos cada 2s          ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Broker: ${BROKER}:${PORT} (TLS)                              ║"
echo "║  Topic:  smarthome/${EQUIPO}/datos                           ║"
echo "║  Usuario: ${USER}                                            ║"
echo "║  Modo:    ${MODO}                                            ║"
echo "║                                                            ║"
echo "║  Presioná Ctrl+C para detener                               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Temperatura base según escenario
case "$MODO" in
  --critico|critico|critica)
    BASE_TEMP=26
    BASE_GAS=450
    MENSAJE="⚠️  Simulando FUGA DE GAS crítica"
    ;;
  --calor|calor|caliente)
    BASE_TEMP=32
    BASE_GAS=300
    MENSAJE="🔥 Simulando TEMPERATURA alta"
    ;;
  --frio|frio|fresco)
    BASE_TEMP=12
    BASE_GAS=250
    MENSAJE="❄️  Simulando TEMPERATURA baja"
    ;;
  *)
    BASE_TEMP=22
    BASE_GAS=300
    MENSAJE="🏠 Hogar normal — datos con variación realista"
    ;;
esac

echo "  ${MENSAJE}"
echo ""

COUNT=0
while true; do
  COUNT=$((COUNT + 1))

  # Variación suave (deriva tipo random walk)
  TEMP=$(printf "%.1f" "$(echo "scale=1; ${BASE_TEMP} + ($RANDOM % 50 - 25) / 10" | bc)")
  HUM=$(printf "%.1f" "$(echo "scale=1; 55 + ($RANDOM % 100 - 50) / 10" | bc)")
  GAS=$(printf "%.0f" "$(echo "scale=0; ${BASE_GAS} + ($RANDOM % 60 - 30)" | bc)")
  SOUND=$(printf "%.0f" "$(echo "scale=0; 25 + ($RANDOM % 40)" | bc)")

  # Si gas supera 400 o temp supera 30, agregar flag de alerta
  ALERTA=""
  if [ "$(echo "$GAS > 400" | bc)" -eq 1 ] || [ "$(echo "$TEMP > 30" | bc)" -eq 1 ]; then
    ALERTA=',"alerta":"Condicion anomala detectada"'
  fi

  PAYLOAD="{\"equipo\":\"${EQUIPO}\",\"temperatura\":${TEMP},\"humedad\":${HUM},\"gas\":${GAS},\"gas_digital\":\"NORMAL\",\"sensor_extra\":${SOUND}${ALERTA}}"

  if mosquitto_pub -h "$BROKER" -p "$PORT" --cafile "$CERTS" \
    -u "$USER" -P "$PASS" \
    -t "smarthome/${EQUIPO}/datos" \
    -m "$PAYLOAD" > /dev/null 2>&1; then
    echo "$(date +%H:%M:%S)  [${COUNT}]  🌡️ ${TEMP}°C  💧 ${HUM}%  🔥 ${GAS}ppm  🔊 ${SOUND}${ALERTA:+ ⚠️ ALERTA}"
  else
    echo "$(date +%H:%M:%S)  [${COUNT}]  ❌ Error publicando — broker reachable?"
  fi

  sleep 2
done
