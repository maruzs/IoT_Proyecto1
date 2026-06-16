# SDD Tasks: T-001 — MQTT Broker con TLS y autenticación

## Executive Summary

| Metric | Value |
|--------|-------|
| Total tasks | **7** |
| Phases | 3 (Infraestructura, Firmware, Servicios) |
| Total estimated lines | **~265** |
| Review budget | 400 lines |
| Budget risk | **Low** (66% of budget) |
| Chained PRs recommended | **No** |
| Decision needed before apply | **No** |

## Phase 1: Infraestructura (P0)

---

### [x] T-001-01: Scripts de generación de certificados y validación

**Priority**: P0 (blocker)
**Dependencies**: None
**Phase**: Infraestructura

**Files affected**:
- `deploy/scripts/generate-certs.sh` — **CREATE** (~95 lines)
- `deploy/mosquitto/config/entrypoint.sh` — **CREATE** (~30 lines)

**Description**:
Create two bash scripts: (1) `generate-certs.sh` — idempotent OpenSSL PKI generator that produces a CA key/cert, server key/cert signed by the CA (SAN: `DNS:mosquitto`, `DNS:localhost`, `IP:127.0.0.1`), and a Mosquitto password file via `mosquitto_passwd`. Reads `MQTT_USER` and `MQTT_PASSWORD` from environment. (2) `entrypoint.sh` — validates all cert files and passwd exist before exec'ing Mosquitto, exits 1 with clear error referencing `generate-certs.sh` if missing.

**Acceptance criteria** (Gherkin):

```
Scenario: Certificate generation produces valid files
  GIVEN OpenSSL is installed
  AND environment variables MQTT_USER and MQTT_PASSWORD are set
  WHEN running `./deploy/scripts/generate-certs.sh`
  THEN deploy/mosquitto/certs/ca.crt exists and is a valid X.509 certificate
  AND deploy/mosquitto/certs/ca.key exists and is a valid RSA private key
  AND deploy/mosquitto/certs/server.crt exists and is signed by the CA
  AND deploy/mosquitto/certs/server.key exists and is a valid RSA private key
  AND server.crt SAN includes DNS:mosquitto, DNS:localhost, IP:127.0.0.1
  AND deploy/mosquitto/config/passwd exists and contains the user entry
  AND all certificates have 365-day expiry

Scenario: Certificate generation is idempotent
  GIVEN certificates already exist in deploy/mosquitto/certs/
  WHEN running `./deploy/scripts/generate-certs.sh` again
  THEN the script completes without error
  AND new certificate files replace the old ones

Scenario: Entrypoint aborts when certs are missing
  GIVEN deploy/mosquitto/certs/ directory is empty or missing files
  WHEN docker compose up is run
  THEN the mosquitto container exits with code 1
  AND the logs contain a clear error message referencing generate-certs.sh
  AND the container does not start mosquitto
```

**Ref spec scenarios**: 1, 2, 5
**Est. lines**: ~125 (95 + 30)

---

### [x] T-001-02: Configuración de Mosquitto y Docker Compose

**Priority**: P0 (blocker)
**Dependencies**: T-001-01 (entrypoint must exist for compose to reference it)
**Phase**: Infraestructura

**Files affected**:
- `deploy/mosquitto/config/mosquitto.conf` — **MODIFY** (~9 lines changed)
- `deploy/docker-compose.yml` — **MODIFY** (~12 lines changed)
- `deploy/.env.example` — **MODIFY** (+4 lines)
- `.gitignore` — **MODIFY** (+3 lines)

**Description**:
1. **mosquitto.conf**: Replace current 1883 listener with two listeners — 8883 (TLS + auth, all interfaces) and 1883 (no auth, `127.0.0.1` only for healthcheck). Add cafile/certfile/keyfile/password_file/allow_anonymous directives.
2. **docker-compose.yml**: Change port mapping from `1883:1883` to `8883:8883`. Add volume mounts for `./mosquitto/certs:/mosquitto/certs:ro` and `./mosquitto/config/passwd:/mosquitto/config/passwd:ro`. Set entrypoint to `entrypoint.sh`. Add `MQTT_USER` and `MQTT_PASSWORD` env vars to mosquitto service. Add cert volume mount to nodered service for TLS config node.
3. **.env.example**: Add `MQTT_USER`, `MQTT_PASSWORD`, `MQTT_TLS_CA`.
4. **.gitignore**: Add `deploy/mosquitto/certs/` and `deploy/mosquitto/config/passwd`.

**Acceptance criteria** (Gherkin):

```
Scenario: Mosquitto starts with TLS and rejects anonymous connections
  GIVEN certificates and passwd file exist
  AND mosquitto container is running
  WHEN a client connects to localhost:8883 without TLS
  THEN the connection is rejected
  WHEN a client connects to localhost:8883 with TLS but no credentials
  THEN the connection is rejected
  WHEN a client connects to localhost:8883 with TLS and valid credentials
  THEN the connection succeeds
  AND the client can publish and subscribe to topics

Scenario: Mosquitto healthcheck works on internal 1883
  GIVEN mosquitto container is running with TLS on 8883
  WHEN Docker runs its healthcheck against port 1883
  THEN the healthcheck succeeds
  WHEN a client from outside Docker tries to connect to localhost:1883
  THEN the connection is refused (bound to 127.0.0.1)

Scenario: Certificates and keys are not committed to git
  GIVEN generate-certs.sh has been run
  AND deploy/mosquitto/certs/ contains ca.crt, ca.key, server.crt, server.key
  AND deploy/mosquitto/config/passwd exists
  WHEN running `git status`
  THEN deploy/mosquitto/certs/ files are not shown as untracked or modified
  AND deploy/mosquitto/config/passwd is not shown as untracked or modified
```

**Ref spec scenarios**: 3, 4, 10
**Est. lines**: ~28 (9 + 12 + 4 + 3)

---

## Phase 2: Firmware (P1)

---

### [x] T-001-03: MKR1000 — Soporte TLS + autenticación

**Priority**: P1
**Dependencies**: T-001-02 (functional broker for integration testing)
**Phase**: Firmware

**Files affected**:
- `src/mkr1000_firmware/src/secrets.h.example` — **MODIFY** (+5 lines, change 1)
- `src/mkr1000_firmware/src/mqtt_manager.h` — **MODIFY** (1 line signature change)
- `src/mkr1000_firmware/src/mqtt_manager.cpp` — **MODIFY** (~12 lines changed)
- `src/mkr1000_firmware/mkr1000_firmware.ino` — **MODIFY** (~3 lines changed)

**Description**:
1. **secrets.h.example**: Add `MQTT_USER`, `MQTT_PASSWORD`, `CA_CERT[]` PEM string constant. Change `MQTT_PORT` from `1883` to `8883`.
2. **mqtt_manager.h**: Change `WiFiClient&` to `WiFiSSLClient&`. Add `port`, `username`, `password`, `caCert` parameters to `initMQTT()`.
3. **mqtt_manager.cpp**: Include `<WiFiSSLClient>`. Change `initMQTT()` to accept new params. Call `setEphemeralKeyPair(true)` on the SSL client. Call `setCACert()` with the embedded CA cert. Pass username and password to `mqttClient.connect()`. Use the `port` parameter in `setServer()`.
4. **mkr1000_firmware.ino**: Change `WiFiClient` to `WiFiSSLClient`. Update `initMQTT()` call to pass all new parameters from `secrets.h`.

**Acceptance criteria** (Gherkin):

```
Scenario: MKR1000 connects with TLS and credentials
  GIVEN MKR1000 firmware is flashed with secrets.h containing CA_CERT, MQTT_USER, MQTT_PASSWORD
  AND MQTT_PORT is set to 8883
  AND Mosquitto is running with TLS on 8883
  WHEN MKR1000 attempts to connect to the broker
  THEN WiFiSSLClient establishes a TLS connection
  THEN the server certificate is validated against the embedded CA cert
  THEN the client authenticates with username and password
  AND the connection succeeds
  AND the client can publish sensor data to MQTT topics
```

**Ref spec scenarios**: 6
**Est. lines**: ~21 (5 + 1 + 12 + 3)

---

### [x] T-001-04: ESP32-CAM — Soporte TLS + autenticación

**Priority**: P1
**Dependencies**: T-001-02 (functional broker for integration testing)
**Phase**: Firmware

**Files affected**:
- `src/esp32cam_firmware/src/secrets.h.example` — **MODIFY** (+5 lines, change 1)
- `src/esp32cam_firmware/src/mqtt_bridge.h` — **MODIFY** (1 line signature change)
- `src/esp32cam_firmware/src/mqtt_bridge.cpp` — **MODIFY** (~12 lines changed)
- `src/esp32cam_firmware/esp32cam_firmware.ino` — **MODIFY** (~3 lines changed)

**Description**:
1. **secrets.h.example**: Add `MQTT_USER`, `MQTT_PASSWORD`, `CA_CERT[]` PEM string constant. Change `MQTT_PORT` from `1883` to `8883`.
2. **mqtt_bridge.h**: Change `WiFiClient&` to `WiFiClientSecure&`. Add `port`, `username`, `password`, `caCert` parameters to `initCameraMQTT()`.
3. **mqtt_bridge.cpp**: Change `initCameraMQTT()` to accept new params. Call `setCACert()` with the embedded CA cert. Pass username and password to `cameraClient.connect()`. Use the `port` parameter in `setServer()`.
4. **esp32cam_firmware.ino**: Change `WiFiClient` to `WiFiClientSecure`. Update `initCameraMQTT()` call to pass all new parameters from `secrets.h`.

**Acceptance criteria** (Gherkin):

```
Scenario: ESP32-CAM connects with TLS and credentials
  GIVEN ESP32-CAM firmware is flashed with secrets.h containing CA_CERT, MQTT_USER, MQTT_PASSWORD
  AND MQTT_PORT is set to 8883
  AND Mosquitto is running with TLS on 8883
  WHEN ESP32-CAM attempts to connect to the broker
  THEN WiFiClientSecure establishes a TLS connection
  THEN the server certificate is validated against the embedded CA cert
  THEN the client authenticates with username and password
  AND the connection succeeds
  AND the client can publish camera images to MQTT topics
```

**Ref spec scenarios**: 7
**Est. lines**: ~21 (5 + 1 + 12 + 3)

---

## Phase 3: Servicios (P1)

---

### [x] T-001-05: Backend Python — Soporte TLS + autenticación

**Priority**: P1
**Dependencies**: T-001-02 (functional broker for integration testing)
**Phase**: Servicios

**Files affected**:
- `src/backend/mqtt_client/client.py` — **MODIFY** (~15 lines changed)

**Description**:
In `MQTTClient.__init__()`:
1. Read `MQTT_PORT` from env (default `"8883"` → cast to int).
2. Read `MQTT_USER` and `MQTT_PASSWORD` from env.
3. Read `MQTT_TLS_CA` from env (path to CA cert).
4. After client creation, call `self.client.tls_set(ca_certs=ca_cert_path)`.
5. Call `self.client.username_pw_set(username=mqtt_user, password=mqtt_password)`.
6. Update default `broker_port` param from `1883` to `8883`.

**Acceptance criteria** (Gherkin):

```
Scenario: Python backend connects with TLS and credentials
  GIVEN environment variables MQTT_PORT=8883, MQTT_USER, MQTT_PASSWORD, MQTT_TLS_CA are set
  AND Mosquitto is running with TLS on 8883
  WHEN the backend MQTTClient initializes
  THEN tls_set() is called with the CA certificate path
  THEN username_pw_set() is called with the credentials
  AND the connection succeeds over TLS
  AND the client can publish and subscribe to MQTT topics
```

**Ref spec scenarios**: 8
**Est. lines**: ~15

---

### [x] T-001-06: Node-RED — Soporte TLS + autenticación

**Priority**: P1
**Dependencies**: T-001-02 (functional broker for integration testing)
**Phase**: Servicios

**Files affected**:
- `nodered/flows.json` — **MODIFY** (~15 lines changed)
- `nodered/flows_cred.json` — **MODIFY** (~5 lines, credentials object)

**Description**:
1. **flows.json**: Modify the `mqtt_broker_config` node (ID `mqtt_broker_config`): change `port` from `"1883"` to `"8883"`, change `usetls` from `false` to `true`, add `"tls"` property referencing a new `tls-config` node. Add new `tls-config` node object with `ca` path set to `/certs/ca.crt`.
2. **flows_cred.json**: Add `credentials` object under the broker config ID with `user` and `password` keys (encrypted by Node-RED at runtime, documented for deployment).

**Acceptance criteria** (Gherkin):

```
Scenario: Node-RED connects with TLS and credentials
  GIVEN Node-RED flows.json has MQTT broker configured on port 8883 with usetls=true
  AND TLS config node references the CA certificate
  AND credentials contain username and password
  AND Mosquitto is running with TLS on 8883
  WHEN Node-RED starts and loads the flows
  THEN the MQTT broker node connects over TLS
  THEN the server certificate is validated against the CA
  THEN authentication succeeds with the provided credentials
  AND Node-RED can publish and subscribe to MQTT topics
```

**Ref spec scenarios**: 9
**Est. lines**: ~20 (15 + 5)

---

### [x] T-001-07: Documentación y sincronización de spec

**Priority**: P2
**Dependencies**: All T-001-01 through T-001-06 (documents final state)
**Phase**: Servicios

**Files affected**:
- `deploy/README.md` — **MODIFY** (~15 lines changed)
- `openspec/specs/infraestructura/spec.md` — **MODIFY** (~20 lines changed)

**Description**:
1. **deploy/README.md**: Add `./scripts/generate-certs.sh` step to quick start. Update port references from `1883` to `8883` (TLS). Update Access table to show `mqtts://localhost:8883`. Document certificate renewal process. Document that firmware must be re-flashed if CA changes. Update troubleshooting to cover cert-related issues.
2. **openspec/specs/infraestructura/spec.md**: Sync R-3 to reflect 8883 TLS + auth listener and 1883 healthcheck-only listener. Sync R-7 for port 8883 reachable from host, 1883 internal only. Ensure all scenarios reference TLS + auth connections.

**Acceptance criteria** (Gherkin):

```
Scenario: Quick start documents cert generation
  GIVEN deploy/README.md is deployed
  WHEN reading the Quick Start section
  THEN it includes the `./scripts/generate-certs.sh` step before `docker compose up -d`
  AND it references MQTT access on port 8883 with TLS
  AND it documents the certificate renewal process

Scenario: Infrastructure spec reflects TLS
  GIVEN openspec/specs/infraestructura/spec.md is current
  WHEN reading R-3
  THEN it specifies port 8883 with TLS + auth
  AND port 1883 as internal-only healthcheck
  WHEN reading R-7
  THEN it specifies port 8883 for host access
  AND port 1883 internal-only
```

**Ref spec scenarios**: 11 (E2E data flow)
**Est. lines**: ~35 (15 + 20)

---

## Review Workload Forecast

| Metric | Value |
|--------|-------|
| Estimated total changed lines | **~265** |
| Review budget | **400 lines** |
| Budget utilization | **66%** |
| Chained PRs recommended | **No** |
| Budget risk | **Low** (well under 400) |
| Decision needed before apply | **No** |

The total estimated line count (~265) is well within the 400-line review budget at 66% utilization. All 7 tasks fit comfortably in a single PR (feature/t-001-mqtt-broker-tls). No chaining is required.

## Task Dependencies Graph

```
T-001-01 (certs + entrypoint)
    └── T-001-02 (mosquitto + compose) [depends on T-001-01]
           ├── T-001-03 (MKR1000) [depends on T-001-02 for testing]
           ├── T-001-04 (ESP32-CAM) [depends on T-001-02 for testing]
           ├── T-001-05 (Python backend) [depends on T-001-02 for testing]
           ├── T-001-06 (Node-RED) [depends on T-001-02 for testing]
           └── T-001-07 (Docs + spec sync) [depends on all]
```

## Task-Level Risks

| Task | Risk | Mitigation |
|------|------|-----------|
| T-001-01 | OpenSSL syntax differences across OS versions | Script tested in Docker Alpine (musl) and Ubuntu (glibc); pin to OpenSSL 3.x features |
| T-001-03 | MKR1000 SRAM overflow with SSL (~2KB extra) | `setEphemeralKeyPair(true)` is mandatory; verify free SRAM after compile |
| T-001-04 | ESP32-CAM heap fragmentation with large MQTT packets + TLS | TLS overhead ~40-60KB heap; existing 60KB buffer may need adjustment |
| T-001-06 | Node-RED `flows_cred.json` credentials format unknown at design time | Document manual credential setup; test after first Node-RED save to capture exact format |
| T-001-07 | Spec may have drifted from actual implementation | Sync spec AFTER all other tasks are implemented, not before |

## Next Recommended Step

**`sdd-apply`** — all 7 tasks can be applied in sequence within the current branch `feature/t-001-mqtt-broker-tls`. No workload guard decision is needed (under 400 lines). Work-unit commit strategy: one commit per task, with tests/docs included in the same commit per `work-unit-commits` skill rules.
