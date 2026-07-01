## Verification Report — t-014-influxdb-ingestion (W1+W2 fixes)

**Change**: t-014-influxdb-ingestion — Multistage Dockerfile with influx CLI + entrypoint.sh retention policy + W1 docs
**Date**: 2026-06-30
**Mode**: Runtime verification (proposal/specs/design not available — task verification only per artifact rules)
**Artifacts verified**: Dockerfile, entrypoint.sh, docker-compose.yml, README.md, mosquitto Dockerfile

---

### Completeness

| Dimension | Status |
|---|---|
| W1 fix (documentation) | ✅ PASS |
| W2 fix (multistage build) | ✅ PASS |
| W2 fix (entrypoint retention) | ❌ FAIL — `--org` flag unsupported |
| W2 fix (INFLUX_HOST env var) | ✅ PASS |
| MQTT telemetry ingestion | ✅ PASS |
| MQTT prediction ingestion | ✅ PASS |
| InfluxDB write & query | ✅ PASS |
| Graceful failure handling | ✅ PASS |

---

### Build Evidence

```
Command: docker compose -f deploy/docker-compose.yml build mqtt-to-influx
Exit: 0
Result: Multi-stage build succeeded (influxdb:2.7 → influx CLI copied → python:3.11-slim)
```

```
Command: docker compose -f deploy/docker-compose.yml up -d --build mosquitto influxdb
Exit: 0
Result: Both containers started. Mosquitto healthy.
```

---

### Runtime Test Evidence

**Environment**: Docker Compose stack (mosquitto, influxdb, mqtt-to-influx)

---

#### Test 1: Retention Policy Application

**Command**: Container startup (entrypoint.sh)
**Expected**: "Retention policy applied successfully."
**Actual**: FAIL — `influx bucket update` rejects `--org` flag

**Evidence**:
```
Incorrect Usage: flag provided but not defined: -org
...
Error: flag provided but not defined: -org
WARNING: Could not set retention policy after 5 retries.
```

**Root cause**: `influx` CLI v2.7 `bucket update` subcommand does not support `--org`. The bucket is identified by `--id` (required flag), not by org+name.

**Current entrypoint.sh command**:
```bash
influx bucket update \
  --host "${INFLUX_HOST}" \
  --token "${INFLUX_TOKEN}" \
  --org smarthome \        # ← UNSUPPORTED FLAG
  --name sensores \        # ← UNSUPPORTED FLAG
  --retention 168h
```

**Required fix**:
```bash
BUCKET_ID=$(influx bucket list \
  --host "${INFLUX_HOST}" \
  --token "${INFLUX_TOKEN}" \
  --org smarthome \
  --json 2>/dev/null | \
  python3 -c "import sys,json; [print(b['id']) for b in json.load(sys.stdin) if b['name']=='sensores']")

if [ -n "$BUCKET_ID" ]; then
  influx bucket update \
    --host "${INFLUX_HOST}" \
    --token "${INFLUX_TOKEN}" \
    --id "$BUCKET_ID" \
    --retention 168h
  echo "Retention policy applied successfully."
else
  echo "WARNING: Could not find sensores bucket ID"
fi
```

**Verified manually**: Sensores bucket already has 168h retention from `DOCKER_INFLUXDB_INIT_RETENTION`:
```
12368bba30d355c4  sensores  168h0m0s  168h0m0s
```

---

#### Test 2: Telemetry Ingestion (smarthome/equipo69/datos)

| Step | Result |
|---|---|
| Publish with mkr1000-equipo69 (has write ACL) | ✅ PASS |
| Bridge receives message | ✅ PASS |
| Bridge writes to InfluxDB | ✅ PASS |
| Flux query returns data | ✅ PASS |

**Log evidence**:
```
2026-06-30 22:59:01,045 [INFO] Ingesting telemetry to InfluxDB: sensor_data,equipo=equipo69 temperatura=99.9,humedad=99.9,gas=999
```

**InfluxDB query evidence**:
```
_result,0,...,2026-06-30T22:59:01Z,999,gas,sensor_data,equipo69
_result,1,...,2026-06-30T22:59:01Z,99.9,humedad,sensor_data,equipo69
_result,2,...,2026-06-30T22:59:01Z,99.9,temperatura,sensor_data,equipo69
```

---

#### Test 3: Prediction Ingestion (smarthome/equipo69/prediccion/temperatura)

| Step | Result |
|---|---|
| Publish with digital-twin-equipo69 (has write ACL) | ✅ PASS |
| Bridge receives prediction message | ✅ PASS |
| Bridge writes to InfluxDB (`sensor_predictions` measurement) | ✅ PASS |
| Flux query returns data | ✅ PASS |

**Log evidence**:
```
2026-06-30 22:59:15,008 [INFO] Ingesting prediction to InfluxDB: sensor_predictions,equipo=equipo69 temperatura=26.8
```

**InfluxDB query evidence**:
```
_result,0,...,2026-06-30T22:59:15Z,26.8,temperatura,sensor_predictions,equipo69
```

---

#### Test 4: ACL Enforcement Verification

**Important discovery**: `mqtt-to-influx-equipo69` has only `topic read` ACL (read-only subscriber). Publishing with these credentials to `smarthome/equipo69/datos` gets silently dropped by Mosquitto ACL. Tests must use write-capable users (mkr1000-equipo69 or digital-twin-equipo69) for publishing.

| Publisher credentials | Topic | ACL write? | Result |
|---|---|---|---|
| mqtt-to-influx-equipo69 | smarthome/equipo69/datos | ❌ No | Message silently dropped |
| mkr1000-equipo69 | smarthome/equipo69/datos | ✅ Yes | ✅ Delivered to bridge |
| digital-twin-equipo69 | smarthome/equipo69/prediccion/temperatura | ✅ Yes | ✅ Delivered to bridge |

---

#### Test 5: W1 Fix (Documentation)

| File | Expected | Found |
|---|---|---|
| `deploy/mosquitto/docker/Dockerfile:31` | Comment about `--build` for acl.conf/entrypoint.sh | ✅ `# ponytail: acl.conf and entrypoint.sh are COPY'd at build time, not bind-mounted.` (line 31-32) |
| `deploy/README.md:128` | Note about rebuild on entrypoint/acl changes | ✅ `**NOTE**: If you modify entrypoint.sh or acl.conf, rebuild the mosquitto image: docker compose up -d --build mosquitto.` (line 128) |

---

### Correctness Table

| Check | Result |
|---|---|
| Multi-stage Dockerfile copies `influx` CLI | ✅ `influx` binary at `/usr/local/bin/influx` |
| entrypoint.sh handles influx unavailability gracefully | ✅ After 5 retries, prints WARNING and continues to Python |
| Python bridge starts after retention attempt | ✅ Log shows `Connected to MQTT. Subscribing to smarthome/equipo69/#...` |
| `INFLUX_HOST` env var in docker-compose | ✅ Present at line 277 |
| Telemetry write to InfluxDB works | ✅ Data queryable via Flux |
| Prediction write to InfluxDB works | ✅ Data queryable via Flux |
| `--org` flag in entrypoint.sh is correct for v2.7 CLI | ❌ Not supported — must use `--id` |

---

### Design Coherence

| Decision | Evidence | Status |
|---|---|---|
| Multistage build copies influx CLI from influxdb:2.7 | Dockerfile Stage 1 copies `/usr/local/bin/influx` | ✅ MATCH |
| Idempotent retention application on every startup | entrypoint.sh retries 5x with 3s delay | ✅ MATCH |
| `--org smarthome` on bucket update | influx CLI v2.7 `bucket update` does not support `--org` | ❌ GAP |
| Graceful failure → Python continues | `set -e` in `&&` chain allows continuation | ✅ MATCH |
| `INFLUX_HOST` env var for container-to-container comms | `http://influxdb:8086` default | ✅ MATCH |

---

### Issues

**CRITICAL**:
- **Retention policy not applied**: `influx bucket update --org smarthome` fails because `--org` is not a valid flag for `bucket update` in influx CLI v2.7. The command must use `--id <bucket-id>` instead, with bucket ID discovered via `influx bucket list --org smarthome --json`. The sensores bucket already has 168h retention from `DOCKER_INFLUXDB_INIT_RETENTION`, so this is a **future-resilience** issue (re-applying on existing volumes fails silently).

**WARNING**: None.

**SUGGESTION**:
- Consider using the `influx` CLI's `--json` flag and `python3` one-liner to parse bucket ID, since `python3` is already available in the container image.

---

### Verdict

**❌ FAIL**

**Passing**: Multistage build, telemetry ingestion, prediction ingestion, InfluxDB writes, graceful failure handling, W1 documentation, `INFLUX_HOST` env var.

**Failing**: entrypoint.sh retention policy application — `influx bucket update` rejects `--org` flag. The fix requires replacing `--org smarthome --name sensores` with `--id $(influx bucket list ... | grep sensores | extract ID)`. Sensores bucket already has correct retention via initial setup, but the idempotent re-apply on container restart is broken.
