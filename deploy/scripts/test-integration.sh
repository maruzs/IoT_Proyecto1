#!/usr/bin/env bash
# =============================================================================
# test-integration.sh — T-001 MQTT TLS Integration Tests
# =============================================================================
# Simula los 4 clientes (MKR1000, ESP32-CAM, Backend, Node-RED) sobre TLS
# y verifica el flujo extremo a extremo sin necesidad de hardware físico.
#
# Uso:
#   export MQTT_USER=equipo69
#   export MQTT_PASSWORD=test123
#   ./deploy/scripts/test-integration.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DEPLOY_DIR="${PROJECT_ROOT}/deploy"
CERTS_DIR="${PROJECT_ROOT}/deploy/mosquitto/certs"
CA_CERT="${CERTS_DIR}/ca.crt"
PASSWD_FILE="${PROJECT_ROOT}/deploy/mosquitto/config/passwd"

BROKER_HOST="localhost"
BROKER_PORT="8883"
MQTT_USER="${MQTT_USER:-equipo69}"
MQTT_PASSWORD="${MQTT_PASSWORD:-test123}"
EQUIPO="equipo69"

PASS=0
FAIL=0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
green()  { echo -e "\033[32m$1\033[0m"; }
red()    { echo -e "\033[31m$1\033[0m"; }
yellow() { echo -e "\033[33m$1\033[0m"; }

mosquitto_pub_tls() {
    # Publish with TLS + auth. Extra args passed through.
    docker run --rm --network host \
        -v "${CERTS_DIR}:/certs:ro" \
        eclipse-mosquitto:2 \
        mosquitto_pub \
        -h "${BROKER_HOST}" -p "${BROKER_PORT}" \
        --cafile /certs/ca.crt \
        -u "${MQTT_USER}" -P "${MQTT_PASSWORD}" \
        "$@"
}

mosquitto_sub_tls() {
    # Subscribe with TLS + auth. Extra args passed through.
    docker run --rm --network host \
        -v "${CERTS_DIR}:/certs:ro" \
        eclipse-mosquitto:2 \
        mosquitto_sub \
        -h "${BROKER_HOST}" -p "${BROKER_PORT}" \
        --cafile /certs/ca.crt \
        -u "${MQTT_USER}" -P "${MQTT_PASSWORD}" \
        "$@"
}

check() {
    local desc="$1"; shift
    if "$@"; then
        green "  ✅ ${desc}"
        PASS=$((PASS + 1))
    else
        red "  ❌ ${desc}"
        FAIL=$((FAIL + 1))
    fi
}

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
echo "============================================================"
echo " T-001 Integration Tests — MQTT TLS + Auth"
echo "============================================================"
echo ""

echo "[1/5] Generating certificates..."
cd "${PROJECT_ROOT}"
MQTT_USER="${MQTT_USER}" MQTT_PASSWORD="${MQTT_PASSWORD}" \
    bash deploy/scripts/generate-certs.sh > /dev/null 2>&1
green "  ✅ Certificates generated"

echo ""
echo "[2/5] Starting Mosquitto..."
cd "${DEPLOY_DIR}"
docker compose down --remove-orphans > /dev/null 2>&1 || true
docker compose up -d mosquitto > /dev/null 2>&1

# Wait for healthy
for i in $(seq 1 15); do
    STATUS=$(docker compose ps mosquitto --format json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Health',''))" 2>/dev/null || echo "")
    if [ "$STATUS" = "healthy" ]; then
        green "  ✅ Mosquitto healthy"
        break
    fi
    sleep 2
done
if [ "$STATUS" != "healthy" ]; then
    red "  ❌ Mosquitto failed to become healthy"
    docker compose logs mosquitto --tail 30
    exit 1
fi

# ---------------------------------------------------------------------------
# Scenario 1 — MKR1000: Publica datos de sensores
# ---------------------------------------------------------------------------
echo ""
echo "[3/5] MKR1000 — Publicación de datos de sensores..."

SENSOR_DATA='{"temperatura":24.5,"humedad":62.1,"gas":0.34,"sonido":0.12,"movimiento":0}'

# Subscribe + publish in parallel
docker run --rm --network host \
    -v "${CERTS_DIR}:/certs:ro" \
    eclipse-mosquitto:2 \
    mosquitto_sub \
    -h "${BROKER_HOST}" -p "${BROKER_PORT}" \
    --cafile /certs/ca.crt \
    -u "${MQTT_USER}" -P "${MQTT_PASSWORD}" \
    -t "smarthome/${EQUIPO}/datos" -C 1 -W 5 > /tmp/mkr1000_test_output.txt 2>&1 &
SUB_PID=$!
sleep 1

mosquitto_pub_tls -t "smarthome/${EQUIPO}/datos" -m "${SENSOR_DATA}" > /dev/null 2>&1
wait $SUB_PID

RECEIVED=$(cat /tmp/mkr1000_test_output.txt 2>/dev/null || echo "")
if echo "$RECEIVED" | grep -q "temperatura"; then
    green "  ✅ MKR1000: datos de sensores publicados y recibidos sobre TLS"
    PASS=$((PASS + 1))
else
    red "  ❌ MKR1000: datos no recibidos"
    FAIL=$((FAIL + 1))
fi

# ---------------------------------------------------------------------------
# Scenario 2 — MKR1000: Publica alerta
# ---------------------------------------------------------------------------
echo ""
echo "  MKR1000 — Publicación de alerta..."

docker run --rm --network host \
    -v "${CERTS_DIR}:/certs:ro" \
    eclipse-mosquitto:2 \
    mosquitto_sub \
    -h "${BROKER_HOST}" -p "${BROKER_PORT}" \
    --cafile /certs/ca.crt \
    -u "${MQTT_USER}" -P "${MQTT_PASSWORD}" \
    -t "smarthome/${EQUIPO}/alerta" -C 1 -W 5 > /tmp/mkr1000_alert.txt 2>&1 &
SUB_PID=$!
sleep 1

mosquitto_pub_tls -t "smarthome/${EQUIPO}/alerta" -m '{"tipo":"gas","nivel":"critico","mensaje":"Fuga detectada"}' > /dev/null 2>&1
wait $SUB_PID

if grep -q "Fuga" /tmp/mkr1000_alert.txt 2>/dev/null; then
    green "  ✅ MKR1000: alerta publicada y recibida sobre TLS"
    PASS=$((PASS + 1))
else
    red "  ❌ MKR1000: alerta no recibida"
    FAIL=$((FAIL + 1))
fi

# ---------------------------------------------------------------------------
# Scenario 3 — MKR1000: Recibe comando de control
# ---------------------------------------------------------------------------
echo ""
echo "  MKR1000 — Recepción de comando de control..."

docker run --rm --network host \
    -v "${CERTS_DIR}:/certs:ro" \
    eclipse-mosquitto:2 \
    mosquitto_sub \
    -h "${BROKER_HOST}" -p "${BROKER_PORT}" \
    --cafile /certs/ca.crt \
    -u "${MQTT_USER}" -P "${MQTT_PASSWORD}" \
    -t "smarthome/${EQUIPO}/control/led" -C 1 -W 5 > /tmp/mkr1000_control.txt 2>&1 &
SUB_PID=$!
sleep 1

mosquitto_pub_tls -t "smarthome/${EQUIPO}/control/led" -m "ON" > /dev/null 2>&1
wait $SUB_PID

if grep -q "ON" /tmp/mkr1000_control.txt 2>/dev/null; then
    green "  ✅ MKR1000: comando de control recibido sobre TLS"
    PASS=$((PASS + 1))
else
    red "  ❌ MKR1000: comando de control no recibido"
    FAIL=$((FAIL + 1))
fi

# ---------------------------------------------------------------------------
# Scenario 4 — ESP32-CAM: Publica evento de cámara
# ---------------------------------------------------------------------------
echo ""
echo "[4/5] ESP32-CAM — Eventos y comandos..."

docker run --rm --network host \
    -v "${CERTS_DIR}:/certs:ro" \
    eclipse-mosquitto:2 \
    mosquitto_sub \
    -h "${BROKER_HOST}" -p "${BROKER_PORT}" \
    --cafile /certs/ca.crt \
    -u "${MQTT_USER}" -P "${MQTT_PASSWORD}" \
    -t "smarthome/${EQUIPO}/camara/evento" -C 1 -W 5 > /tmp/esp32cam_event.txt 2>&1 &
SUB_PID=$!
sleep 1

mosquitto_pub_tls -t "smarthome/${EQUIPO}/camara/evento" -m '{"status":"camara_lista"}' > /dev/null 2>&1
wait $SUB_PID

if grep -q "camara_lista" /tmp/esp32cam_event.txt 2>/dev/null; then
    green "  ✅ ESP32-CAM: evento de cámara publicado y recibido sobre TLS"
    PASS=$((PASS + 1))
else
    red "  ❌ ESP32-CAM: evento no recibido"
    FAIL=$((FAIL + 1))
fi

# ---------------------------------------------------------------------------
# Scenario 5 — ESP32-CAM: Recibe comando de captura
# ---------------------------------------------------------------------------
echo ""
echo "  ESP32-CAM — Comando de captura..."

docker run --rm --network host \
    -v "${CERTS_DIR}:/certs:ro" \
    eclipse-mosquitto:2 \
    mosquitto_sub \
    -h "${BROKER_HOST}" -p "${BROKER_PORT}" \
    --cafile /certs/ca.crt \
    -u "${MQTT_USER}" -P "${MQTT_PASSWORD}" \
    -t "smarthome/${EQUIPO}/camara/captura" -C 1 -W 5 > /tmp/esp32cam_cmd.txt 2>&1 &
SUB_PID=$!
sleep 1

mosquitto_pub_tls -t "smarthome/${EQUIPO}/camara/captura" -m "capturar" > /dev/null 2>&1
wait $SUB_PID

if grep -q "capturar" /tmp/esp32cam_cmd.txt 2>/dev/null; then
    green "  ✅ ESP32-CAM: comando de captura recibido sobre TLS"
    PASS=$((PASS + 1))
else
    red "  ❌ ESP32-CAM: comando de captura no recibido"
    FAIL=$((FAIL + 1))
fi

# ---------------------------------------------------------------------------
# Scenario 6 — Anónimo rechazado (regresión)
# ---------------------------------------------------------------------------
echo ""
echo "  Seguridad — Anónimo rechazado..."

cd "${DEPLOY_DIR}"
timeout 5 docker exec deploy-mosquitto-1 mosquitto_pub \
    -h 127.0.0.1 -p 8883 \
    --cafile /mosquitto/certs/ca.crt \
    -t "smarthome/${EQUIPO}/datos" -m "anon" \
    > /dev/null 2>&1; EXIT_CODE=$?

if [ "$EXIT_CODE" -ne 0 ]; then
    green "  ✅ Anónimo rechazado (exit code: ${EXIT_CODE})"
    PASS=$((PASS + 1))
else
    red "  ❌ Anónimo aceptado — regresión de seguridad"
    FAIL=$((FAIL + 1))
fi

# ---------------------------------------------------------------------------
# Scenario 7 — Reconexión: healthcheck sigue funcional
# ---------------------------------------------------------------------------
echo ""
echo "[5/5] Healthcheck — listener 1883 interno..."

HC_OUTPUT=$(timeout 5 docker exec deploy-mosquitto-1 \
    mosquitto_sub -h 127.0.0.1 -p 1883 \
    -t '$SYS/broker/uptime' -C 1 -W 3 2>&1 || echo "FAILED")

if echo "$HC_OUTPUT" | grep -q "seconds"; then
    green "  ✅ Healthcheck funcional en 1883 (anónimo, solo localhost)"
    PASS=$((PASS + 1))
else
    red "  ❌ Healthcheck falló: ${HC_OUTPUT}"
    FAIL=$((FAIL + 1))
fi

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
echo ""
echo "============================================================"
cd "${DEPLOY_DIR}"
docker compose down > /dev/null 2>&1
rm -rf "${CERTS_DIR}" "${PASSWD_FILE}" /tmp/mkr1000_*.txt /tmp/esp32cam_*.txt

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
TOTAL=$((PASS + FAIL))
echo " Resultados: ${PASS}/${TOTAL} pasaron"
echo "============================================================"

if [ "$FAIL" -eq 0 ]; then
    green " ✅ TODOS los escenarios de integración pasaron"
    exit 0
else
    red " ❌ ${FAIL} escenario(s) fallaron"
    exit 1
fi
