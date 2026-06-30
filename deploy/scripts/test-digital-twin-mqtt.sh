#!/usr/bin/env bash
# =============================================================================
# test-digital-twin-mqtt.sh — T-007 Digital Twin MQTT integration tests
# =============================================================================
# Verifica que el Digital Twin consume datos de sensores por MQTT, expone su
# estado por HTTP y publica predicciones de vuelta a MQTT.
#
# Uso:
#   ./deploy/scripts/test-digital-twin-mqtt.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DEPLOY_DIR="${PROJECT_ROOT}/deploy"
CERTS_DIR="${PROJECT_ROOT}/deploy/mosquitto/certs"

BROKER_HOST="localhost"
BROKER_PORT="8883"
EQUIPO="equipo69"

PASS=0
FAIL=0

MQTT_USER_DIGITALTWIN="${MQTT_USER_DIGITALTWIN:-digital-twin-equipo69}"
MQTT_PASS_DIGITALTWIN="${MQTT_PASS_DIGITALTWIN:-testpass123}"
MQTT_USER_MKR1000="${MQTT_USER_MKR1000:-mkr1000-equipo69}"
MQTT_PASS_MKR1000="${MQTT_PASS_MKR1000:-testpass123}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
green()  { echo -e "\033[32m$1\033[0m"; }
red()    { echo -e "\033[31m$1\033[0m"; }
yellow() { echo -e "\033[33m$1\033[0m"; }

mosquitto_pub_user() {
    # Publish with TLS + auth using per-client credentials.
    local user="$1"; shift
    local pass="$1"; shift
    docker run --rm --network host \
        -v "${CERTS_DIR}:/certs:ro" \
        eclipse-mosquitto:2 \
        mosquitto_pub \
        -h "${BROKER_HOST}" -p "${BROKER_PORT}" \
        --cafile /certs/ca.crt \
        -u "${user}" -P "${pass}" \
        "$@"
}

mosquitto_sub_user() {
    # Subscribe with TLS + auth using per-client credentials.
    local user="$1"; shift
    local pass="$1"; shift
    docker run --rm --network host \
        -v "${CERTS_DIR}:/certs:ro" \
        eclipse-mosquitto:2 \
        mosquitto_sub \
        -h "${BROKER_HOST}" -p "${BROKER_PORT}" \
        --cafile /certs/ca.crt \
        -u "${user}" -P "${pass}" \
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

# HTTP GET helper using the curl Docker image.
http_get() {
    docker run --rm --network host curlimages/curl:8.12.1 \
        -s --max-time 5 "$@"
}

# HTTP POST helper using the curl Docker image.
http_post() {
    docker run --rm --network host curlimages/curl:8.12.1 \
        -s --max-time 5 -X POST "$@"
}

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
echo "============================================================"
echo " T-007 Digital Twin → MQTT integration tests"
echo "============================================================"
echo ""

echo "[1/4] Preparing certificates..."
cd "${PROJECT_ROOT}"
bash deploy/scripts/generate-certs.sh > /dev/null 2>&1 || true
green "  ✅ Certificates ready"

echo ""
echo "[2/4] Starting Mosquitto + Digital Twin..."
cd "${DEPLOY_DIR}"
docker compose down --remove-orphans > /dev/null 2>&1 || true
# ponytail: speed up consolidation so 6 readings build enough history for predictions
CONSOLIDATION_INTERVAL=1 PREDICTION_INTERVAL=600 \
    docker compose up -d mosquitto digital-twin > /dev/null 2>&1

# Wait for Mosquitto healthy
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

# Wait for Digital Twin HTTP endpoint
for i in $(seq 1 15); do
    if http_get "http://localhost:8003/health" > /tmp/dt_health.txt 2>&1; then
        green "  ✅ Digital Twin reachable"
        break
    fi
    sleep 2
done
if ! http_get "http://localhost:8003/health" > /tmp/dt_health.txt 2>&1; then
    red "  ❌ Digital Twin failed to become reachable"
    docker compose logs digital-twin --tail 30
    exit 1
fi

# ---------------------------------------------------------------------------
# Scenario — MQTT datos → Digital Twin state + predictions
# ---------------------------------------------------------------------------
echo ""
echo "[3/4] Publishing 6 sensor readings to MQTT..."

# Publish 6 readings, 1s apart, with monotonically changing values
for i in $(seq 1 6); do
    TEMP=$(python3 -c "print(20.0 + $i * 0.5)")
    HUM=$(python3 -c "print(50.0 + $i * 2.0)")
    GAS=$(python3 -c "print(300.0 + $i * 10.0)")
    mosquitto_pub_user "${MQTT_USER_MKR1000}" "${MQTT_PASS_MKR1000}" \
        -t "smarthome/${EQUIPO}/datos" \
        -m "{\"temperatura\":${TEMP},\"humedad\":${HUM},\"gas\":${GAS}}" > /dev/null 2>&1
    sleep 1
done
LAST_TEMP=23.0
LAST_HUM=62.0
LAST_GAS=360.0

echo "  Waiting for Digital Twin to consolidate readings..."
sleep 5

echo ""
echo "[4/4] Verifying Digital Twin state and predictions..."

# Path A: GET /gemelo/estado returns the last sensor readings
STATE=$(http_get "http://localhost:8003/gemelo/estado" 2>/dev/null || echo "{}")
STATE_TEMP=$(echo "$STATE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('estado_actual',{}).get('temperatura','MISSING'))" 2>/dev/null || echo "MISSING")
STATE_HUM=$(echo "$STATE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('estado_actual',{}).get('humedad','MISSING'))" 2>/dev/null || echo "MISSING")
STATE_GAS=$(echo "$STATE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('estado_actual',{}).get('gas','MISSING'))" 2>/dev/null || echo "MISSING")

if [ "$STATE_TEMP" = "$LAST_TEMP" ]; then
    green "  ✅ /gemelo/estado temperatura matches last MQTT reading (${LAST_TEMP})"
    PASS=$((PASS + 1))
else
    red "  ❌ /gemelo/estado temperatura mismatch (got ${STATE_TEMP}, expected ${LAST_TEMP})"
    FAIL=$((FAIL + 1))
fi

if [ "$STATE_HUM" = "$LAST_HUM" ]; then
    green "  ✅ /gemelo/estado humedad matches last MQTT reading (${LAST_HUM})"
    PASS=$((PASS + 1))
else
    red "  ❌ /gemelo/estado humedad mismatch (got ${STATE_HUM}, expected ${LAST_HUM})"
    FAIL=$((FAIL + 1))
fi

if [ "$STATE_GAS" = "$LAST_GAS" ]; then
    green "  ✅ /gemelo/estado gas matches last MQTT reading (${LAST_GAS})"
    PASS=$((PASS + 1))
else
    red "  ❌ /gemelo/estado gas mismatch (got ${STATE_GAS}, expected ${LAST_GAS})"
    FAIL=$((FAIL + 1))
fi

# Start prediction subscriber AFTER readings are published and consolidated
PRED_FILE="/tmp/dt_pred.txt"
mosquitto_sub_user "${MQTT_USER_DIGITALTWIN}" "${MQTT_PASS_DIGITALTWIN}" \
    -t "smarthome/${EQUIPO}/prediccion/+" -C 3 -W 15 > "$PRED_FILE" 2>&1 &
SUB_PID=$!
sleep 2

# Path B: Trigger predictions and wait for MQTT publishes
PRE_OUT=$(http_post "http://localhost:8003/gemelo/predecir" 2>/dev/null || echo "PREDICT_FAILED")
if echo "$PRE_OUT" | grep -q "Prediction calculated"; then
    green "  ✅ /gemelo/predecir returned success"
    PASS=$((PASS + 1))
else
    red "  ❌ /gemelo/predecir failed: ${PRE_OUT}"
    FAIL=$((FAIL + 1))
fi

wait "$SUB_PID" 2>/dev/null || true
PRED_COUNT=$(wc -l < "$PRED_FILE" 2>/dev/null || echo 0)
if [ "$PRED_COUNT" -ge 3 ]; then
    green "  ✅ Received ${PRED_COUNT} prediction messages on MQTT"
    PASS=$((PASS + 1))
else
    red "  ❌ Expected ≥3 prediction messages, got ${PRED_COUNT}"
    FAIL=$((FAIL + 1))
fi

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
echo ""
echo "============================================================"
cd "${DEPLOY_DIR}"
docker compose down > /dev/null 2>&1
rm -f /tmp/dt_*.txt

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
TOTAL=$((PASS + FAIL))
echo " Resultados: ${PASS}/${TOTAL} pasaron"
echo "============================================================"

if [ "$FAIL" -eq 0 ]; then
    green " ✅ TODOS los escenarios Digital Twin→MQTT pasaron"
    exit 0
else
    red " ❌ ${FAIL} escenario(s) fallaron"
    exit 1
fi
