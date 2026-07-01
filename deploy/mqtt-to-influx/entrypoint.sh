#!/usr/bin/env sh
# =============================================================================
# entrypoint.sh — MQTT to InfluxDB bridge startup
# =============================================================================
# 1. Ensures InfluxDB bucket retention policy is applied (idempotent)
# 2. Starts the Python ingestion script
# =============================================================================

set -e

# ---------------------------------------------------------------------------
# Apply InfluxDB retention (idempotent — runs on every startup)
# ---------------------------------------------------------------------------
# This handles the case where DOCKER_INFLUXDB_INIT_RETENTION only applied
# on first init. Running it here ensures existing volumes also get the policy.
#
# influx v2.7 CLI: bucket list supports --name, bucket update requires --id.
# ---------------------------------------------------------------------------
INFLUX_HOST="${INFLUX_HOST:-http://influxdb:8086}"
RETRY=0
MAX_RETRIES=25

echo "Applying InfluxDB retention policy (7 days)..."
until [ $RETRY -ge $MAX_RETRIES ]; do
  # Get bucket ID by name (influx v2.7 list supports --name)
  BUCKET_ID=$(influx bucket list \
    --host "${INFLUX_HOST}" \
    --token "${INFLUX_TOKEN}" \
    --name sensores \
    --json 2>/dev/null | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['id'] if d else '')" 2>/dev/null) || BUCKET_ID=""

  if [ -n "$BUCKET_ID" ]; then
    influx bucket update \
      --host "${INFLUX_HOST}" \
      --token "${INFLUX_TOKEN}" \
      --id "$BUCKET_ID" \
      --retention 168h 2>&1 && {
      echo "Retention policy applied successfully."
      break
    }
  fi

  RETRY=$((RETRY + 1))
  if [ $RETRY -lt $MAX_RETRIES ]; then
    echo "InfluxDB not ready yet, retrying in 3s... (${RETRY}/${MAX_RETRIES})"
    sleep 3
  else
    echo "WARNING: Could not set retention after ${MAX_RETRIES} retries."
    echo "Run manually:"
    echo "  influx bucket update --id \$(influx bucket list --name sensores --json | python3 -c \"import sys,json; print(json.load(sys.stdin)[0]['id'])\") --retention 168h"
  fi
done

# ---------------------------------------------------------------------------
# Start the ingestion script
# ---------------------------------------------------------------------------
exec python mqtt_to_influx.py
