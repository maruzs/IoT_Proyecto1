#!/usr/bin/env bash
# =============================================================================
# test-coap-mqtt.sh — T-005/T-006 CoAP Bridge → MQTT integration tests
# =============================================================================
# Verifica que el CoAP Bridge recibe POSTs por UDP y los publica en MQTT
# sobre TLS con las credenciales correctas de ACL.
#
# Uso:
#   ./deploy/scripts/test-coap-mqtt.sh
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
MQTT_USER_COAPBRIDGE="${MQTT_USER_COAPBRIDGE:-coap-bridge-equipo69}"
MQTT_PASS_COAPBRIDGE="${MQTT_PASS_COAPBRIDGE:-testpass123}"

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

# Run a CoAP POST against /sensores/temperatura with the given Python literal payload.
coap_post() {
    local payload="$1"
    local tmpfile
    tmpfile=$(mktemp /tmp/coap_post_XXXXXX.py)
    cat > "$tmpfile" <<PY
import asyncio, json
from aiocoap import Context, Message
from aiocoap.numbers.codes import Code
async def post():
    ctx = await Context.create_client_context()
    req = Message(
        code=Code.POST,
        payload=json.dumps(${payload}).encode(),
        uri="coap://localhost:5683/sensores/temperatura",
    )
    resp = await ctx.request(req).response
    print(f"CoAP response: {resp.code}")
asyncio.run(post())
PY
    docker run --rm --network host \
        -v "${tmpfile}:/tmp/coap_post.py:ro" \
        python:3.11-slim \
        sh -c "pip install -q aiocoap && python3 /tmp/coap_post.py"
    rm -f "$tmpfile"
}

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
echo "============================================================"
echo " T-005/T-006 CoAP Bridge → MQTT integration tests"
echo "============================================================"
echo ""

echo "[1/3] Preparing certificates..."
cd "${PROJECT_ROOT}"
bash deploy/scripts/generate-certs.sh > /dev/null 2>&1 || true
green "  ✅ Certificates ready"

echo ""
echo "[2/3] Starting Mosquitto + CoAP Bridge..."
cd "${DEPLOY_DIR}"
docker compose down --remove-orphans > /dev/null 2>&1 || true
docker compose up -d mosquitto coap-bridge > /dev/null 2>&1

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

# Wait for CoAP Bridge to be reachable (no compose healthcheck defined)
for i in $(seq 1 15); do
    if coap_post '{"temperatura":0.1}' > /tmp/coap_ping.txt 2>&1; then
        green "  ✅ CoAP Bridge reachable"
        break
    fi
    sleep 2
done
if ! coap_post '{"temperatura":0.1}' > /tmp/coap_ping.txt 2>&1; then
    red "  ❌ CoAP Bridge failed to become reachable"
    docker compose logs coap-bridge --tail 30
    exit 1
fi

# ---------------------------------------------------------------------------
# Scenario 1 — CoAP POST temperatura → MQTT sensores/temperatura
# ---------------------------------------------------------------------------
echo ""
echo "[3/3] Scenario 1 — CoAP POST temperatura → MQTT..."

SUB_FILE="/tmp/coap_mqtt_sub.txt"
mosquitto_sub_user "${MQTT_USER_DIGITALTWIN}" "${MQTT_PASS_DIGITALTWIN}" \
    -t "smarthome/${EQUIPO}/sensores/temperatura" -C 1 -W 15 > "$SUB_FILE" 2>&1 &
SUB_PID=$!
sleep 3

COAP_OUT=$(coap_post '{"temperatura":25.3}' 2>&1 || echo "COAP_FAILED")
wait "$SUB_PID" || true

if echo "$COAP_OUT" | grep -qi "changed"; then
    green "  ✅ CoAP POST returned CHANGED"
    PASS=$((PASS + 1))
else
    red "  ❌ CoAP POST did not return CHANGED: ${COAP_OUT}"
    FAIL=$((FAIL + 1))
fi

if grep -q "25.3" "$SUB_FILE" 2>/dev/null; then
    green "  ✅ MQTT subscriber received temperatura=25.3"
    PASS=$((PASS + 1))
else
    red "  ❌ MQTT subscriber did not receive temperatura"
    FAIL=$((FAIL + 1))
fi

# ---------------------------------------------------------------------------
# Scenario 2 — CoAP POST with missing field returns 4.00 and no MQTT publish
# ---------------------------------------------------------------------------
echo ""
echo "  Scenario 2 — CoAP POST missing field → 4.00 Bad Request..."

SUB_FILE="/tmp/coap_mqtt_neg.txt"
mosquitto_sub_user "${MQTT_USER_DIGITALTWIN}" "${MQTT_PASS_DIGITALTWIN}" \
    -t "smarthome/${EQUIPO}/sensores/temperatura" -C 1 -W 10 > "$SUB_FILE" 2>&1 &
SUB_PID=$!
sleep 3

set +e
COAP_OUT=$(coap_post '{"humedad":60}' 2>&1)
wait "$SUB_PID" 2>/dev/null
SUB_EXIT=$?
set -e

if echo "$COAP_OUT" | grep -qi "bad request"; then
    green "  ✅ CoAP POST missing field returned Bad Request"
    PASS=$((PASS + 1))
else
    red "  ❌ CoAP POST did not return BAD_REQUEST: ${COAP_OUT}"
    FAIL=$((FAIL + 1))
fi

if [ "$SUB_EXIT" -eq 27 ] || [ "$SUB_EXIT" -eq 143 ]; then
    green "  ✅ No MQTT message published for invalid payload"
    PASS=$((PASS + 1))
else
    red "  ❌ Unexpected MQTT message received (subscriber exit=${SUB_EXIT})"
    FAIL=$((FAIL + 1))
fi

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
echo ""
echo "============================================================"
cd "${DEPLOY_DIR}"
docker compose down > /dev/null 2>&1
rm -f /tmp/coap_*.txt

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
TOTAL=$((PASS + FAIL))
echo " Resultados: ${PASS}/${TOTAL} pasaron"
echo "============================================================"

if [ "$FAIL" -eq 0 ]; then
    green " ✅ TODOS los escenarios CoAP→MQTT pasaron"
    exit 0
else
    red " ❌ ${FAIL} escenario(s) fallaron"
    exit 1
fi
