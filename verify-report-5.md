## Verification Report — PR1 Critical Fixes (Round 5)

**Change**: PR1 — Critical Fixes (ACL read/write mismatch + timeout wrapper)
**Date**: 2026-06-26
**Mode**: Full artifact verification (proposal, specs, design, tasks)
**Artifacts verified**: `deploy/scripts/test-integration.sh`

---

### Completeness

| Dimension | Status |
|---|---|
| Task completion | 13/14 tasks pass, 1 fails |
| Build / syntax | `bash -n` PASS |
| Runtime tests | 13/14 scenarios pass |
| Spec compliance | 13/14 scenario requirements met |

---

### Build / Syntax Evidence

```
Command: bash -n deploy/scripts/test-integration.sh
Exit: 0
Result: SYNTAX OK
```

---

### Test Evidence

**Command**: `bash deploy/scripts/test-integration.sh`
**Exit code**: 1 (1 scenario failed)

| Scenario | Description | Result |
|---|---|---|
| 1 | MKR1000 — datos de sensores | ✅ PASS |
| 2 | MKR1000 — alerta | ✅ PASS |
| 3 | MKR1000 — comando de control | ✅ PASS |
| 4 | ESP32-CAM — evento de cámara | ✅ PASS |
| 5 | ESP32-CAM — comando de captura | ✅ PASS |
| 6 | Anónimo rechazado (regresión) | ✅ PASS (CI-verified) |
| 7 | Healthcheck — `$SYS/broker/uptime` | ❌ FAIL — Timed out |
| 8a | Negative ACL: mkr1000 → camara/imagen | ✅ PASS |
| 8b | Negative ACL: esp32cam → datos | ✅ PASS |
| 8c | Negative ACL: backend → alerta | ✅ PASS |
| 8d | Negative ACL: nodered → llm/decision | ✅ PASS |
| 8e | Negative ACL: llm-gateway → datos | ✅ PASS |
| 8f | Negative ACL: digital-twin → control/led | ✅ PASS |
| 8g | Negative ACL: coap-bridge → datos | ✅ PASS |

---

### Spec Compliance Matrix

| Requirement | Scenario | Evidence | Status |
|---|---|---|---|
| MKR1000 publish datos (write ACL) | Scenario 1 | `mosquitto_pub_user mkr1000` → received by nodered | ✅ PASS |
| MKR1000 publish alerta (write ACL) | Scenario 2 | `mosquitto_pub_user mkr1000` → received by digital-twin | ✅ PASS |
| MKR1000 receive control/led (read ACL) | Scenario 3 | `mosquitto_sub_user mkr1000` ← published by nodered | ✅ PASS |
| ESP32-CAM publish evento (write ACL) | Scenario 4 | `mosquitto_pub_user esp32cam` → received by nodered | ✅ PASS |
| ESP32-CAM receive captura (read ACL) | Scenario 5 | `mosquitto_sub_user esp32cam` ← published by backend | ✅ PASS |
| Anonymous rejected (TLS 8883) | Scenario 6 | CONNACK 5 verified in CI | ✅ PASS |
| Healthcheck over TLS | Scenario 7 | Timed out — `$SYS/broker/uptime` not reachable via TLS | ❌ FAIL |
| ACL enforcement: mkr1000 denied camara | Scenario 8a | subscribe-first pattern → exit 27 (no delivery) | ✅ PASS |
| ACL enforcement: esp32cam denied datos | Scenario 8b | subscribe-first pattern → exit 27 | ✅ PASS |
| ACL enforcement: backend denied alerta | Scenario 8c | subscribe-first pattern → exit 27 | ✅ PASS |
| ACL enforcement: nodered denied llm | Scenario 8d | subscribe-first pattern → exit 27 | ✅ PASS |
| ACL enforcement: llm-gateway denied datos | Scenario 8e | subscribe-first pattern → exit 27 | ✅ PASS |
| ACL enforcement: digital-twin denied control | Scenario 8f | subscribe-first pattern → exit 27 | ✅ PASS |
| ACL enforcement: coap-bridge denied datos | Scenario 8g | subscribe-first pattern → exit 27 | ✅ PASS |

---

### Scenario 7 Root Cause Analysis

**Symptom**: `mosquitto_sub_user nodered-smarthome -t '$SYS/broker/uptime'` times out (exit 27).

**Root cause**: Missing ACL entry. No user in `deploy/mosquitto/config/acl.conf` has `topic read $SYS/#`.  
In Mosquitto with `acl_file` active, `$SYS` topics are subject to ACL checks like any other topic.  
The subscription is accepted at the protocol level, but the broker silently drops `$SYS` messages because no ACL grants read access.

**Evidence**:
- `$SYS/broker/uptime` returns data (e.g., `22 seconds`) from inside the container on `127.0.0.1:1883` (anonymous, no ACL).
- `mosquitto_sub -u nodered-smarthome -t 'smarthome/equipo69/datos'` on port 8883 (TLS) works correctly (allowed topic).
- `mosquitto_sub -u nodered-smarthome -t '$SYS/broker/uptime'` on port 8883 (TLS) times out with exit 27.

**Design note**: The original `design.md` (infraestructura) noted this as an unchecked item:
> Health check: `mosquitto_sub -t '$SYS/broker/uptime'` requires `$SYS` messages to be enabled (default in Mosquitto 2.x). If disabled, fallback to `nc -z localhost 1883`.

The previous fix (adding `-W 3` timeout wrapper) only prevented indefinite hanging; it did not address the root ACL denial.

**Fix required**: Add `topic read $SYS/#` to the `nodered-smarthome` ACL entry in `deploy/mosquitto/config/acl.conf`.

---

### Correctness Table

| Check | Result |
|---|---|
| Previous ACL fixes (scenarios 1–5) work correctly | ✅ Confirmed |
| `check_denied` helper with subscribe-first pattern | ✅ All 7 negative ACLs pass |
| `set -euo pipefail` + `set +e` scoping in `check_denied` | ✅ Correctly scoped |
| Timeout wrapper on scenario 7 | ⚠️ Prevents hang, does not fix failure |
| Cleanup (`docker compose down`, temp file removal) | ✅ Works |

---

### Design Coherence

| Decision | Evidence | Status |
|---|---|---|
| subscribe-first ACL verification pattern | `check_denied()` — works around Mosquitto 1.6 silent-drop | ✅ MATCH |
| Per-client credentials (`mosquitto_pub_user`/`mosquitto_sub_user`) | All 7 ACL users used correctly | ✅ MATCH |
| Healthcheck via `$SYS/broker/uptime` on TLS | Missing ACL grant → timeout | ❌ GAP |
| Negative ACL test coverage | Covers all 7 users | ✅ COMPLETE |

---

### Issues

**CRITICAL**:
- **Scenario 7 FAIL**: `$SYS/broker/uptime` subscription over TLS port 8883 times out because `nodered-smarthome` lacks ACL read access to `$SYS/#`. The previous fix (`-W 3` timeout wrapper) only prevented hanging but didn't resolve the delivery failure.

**WARNING**: None.

**SUGGESTION**: None.

---

### Verdict

**❌ FAIL**

13 of 14 scenarios pass. Scenario 7 (healthcheck via `$SYS/broker/uptime` over TLS) fails with root cause: missing `topic read $SYS/#` ACL entry for `nodered-smarthome`. All six previous critical fixes (scenarios 1–5 ACL mismatches, scenario 7 timeout wrapper) are confirmed working correctly.
