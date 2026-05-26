# SDD Delta Spec: Spec 00 — Infraestructura de Contenedores

## Summary

Docker Compose infrastructure for Mosquitto MQTT broker + Node-RED, isolated in `deploy/` at project root. This is the foundational spec that all specs 01-07 depend on.

---

## ADDED

### A-1: `deploy/docker-compose.yml`

A Docker Compose v2 file defining two services:

**Service `mosquitto`:**
- Image: `eclipse-mosquitto:2` (latest stable 2.x)
- Port mapping: `1883:1883`
- Volume mount: `./mosquitto/config/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro`
- Volume mount: `mosquitto_data:/mosquitto/data` (Docker named volume for persistence)
- Volume mount: `mosquitto_logs:/mosquitto/log` (Docker named volume for logs)
- Restart policy: `unless-stopped`
- Health check: `mosquitto_sub -t '$SYS/#' -C 1 -E` or equivalent TCP check on port 1883

**Service `nodered`:**
- Image: built from `./nodered/Dockerfile` (derived from `nodered/node-red:3-lts`)
- Port mapping: `1880:1880`
- Volume mount: `./nodered/data:/data` (bind mount for flows, settings, credentials)
- `depends_on: mosquitto` with `condition: service_healthy`
- Restart policy: `unless-stopped`
- Environment: `TZ` set to local timezone

**Named volumes declared:**
- `mosquitto_data`
- `mosquitto_logs`

### A-2: `deploy/nodered/Dockerfile`

A Dockerfile derived from `nodered/node-red:3-lts` that preinstalls required nodes:

```dockerfile
FROM nodered/node-red:3-lts
RUN npm install --no-audit --no-fund \
    node-red-dashboard \
    node-red-contrib-tfjs-coco-ssd \
    node-red-node-email \
    node-red-contrib-telegrambot
```

### A-3: `deploy/mosquitto/config/mosquitto.conf`

Mosquitto broker configuration:

```
listener 1883 0.0.0.0
allow_anonymous true
persistence true
persistence_location /mosquitto/data/
log_dest file /mosquitto/log/mosquitto.log
```

### A-4: `deploy/nodered/data/` (directory)

Empty directory created as bind mount target. Must contain after first run:
- `flows.json` — Node-RED flow definitions
- `flows_cred.json` — Encrypted credentials
- `settings.js` — Node-RED settings

### A-5: `deploy/README.md`

Documentation containing:
- Prerequisites (Docker v24+, Docker Compose v2+)
- Quick start: `cd deploy && docker compose up -d`
- Access URLs: `http://localhost:1880` (Node-RED), `localhost:1883` (Mosquitto)
- How to stop: `docker compose down`
- Persistence behavior explanation
- Resource requirements (Mosquitto: 64MB RAM, Node-RED: 256MB+ RAM)
- Troubleshooting section (port conflicts, permission issues on bind mounts)
- How to verify services are running

### A-6: `.gitignore` entries (if not present)

```
deploy/nodered/data/flows_cred.json
deploy/mosquitto/log/
```

---

## MODIFIED

None. This change is fully isolated to the new `deploy/` directory.

---

## REMOVED

None.

---

## Requirements

### R-1: Directory Structure

After implementation, the following tree MUST exist:

```
deploy/
├── docker-compose.yml
├── mosquitto/
│   └── config/
│       └── mosquitto.conf
├── nodered/
│   ├── Dockerfile
│   └── data/
└── README.md
```

### R-2: Docker Compose Compatibility

- `docker-compose.yml` MUST use Compose specification (no `version:` key, or `version: "3.8"` for backward compatibility)
- MUST be compatible with Docker Compose v2.x
- MUST define exactly two services: `mosquitto` and `nodered`

### R-3: Mosquitto Configuration

- MUST listen on port 1883 on all interfaces (`0.0.0.0`)
- MUST allow anonymous connections (`allow_anonymous true`)
- MUST have disk persistence enabled (`persistence true`)
- MUST NOT require username/password
- Config file MUST be mounted as read-only (`:ro`)

### R-4: Node-RED Configuration

- MUST be built from a Dockerfile extending `nodered/node-red:3-lts`
- MUST have `depends_on` with health condition for mosquitto
- MUST use bind mount `./nodered/data:/data` (not a named volume)
- MUST expose port 1880 to host

### R-5: Preinstalled Nodes

The Node-RED image MUST include these npm packages at build time:
- `node-red-dashboard`
- `node-red-contrib-tfjs-coco-ssd`
- `node-red-node-email`
- `node-red-contrib-telegrambot`

### R-6: Persistence

- Node-RED `data/` directory MUST be a bind mount (survives `docker compose down`)
- Mosquitto data MUST use a named volume (survives `docker compose down`)
- Files in `deploy/nodered/data/` MUST NOT be deleted by `docker compose down`

### R-7: Network

- Both services MUST be on the same Docker Compose default network
- Mosquitto MUST be reachable from Node-RED via hostname `mosquitto`
- Port 1883 MUST be reachable from host at `localhost:1883`
- Port 1880 MUST be reachable from host at `http://localhost:1880`

### R-8: Documentation

`deploy/README.md` MUST contain:
- Prerequisites section
- Quick start commands (up, down, logs)
- Access URLs
- Persistence explanation
- Resource requirements
- Troubleshooting section

---

## Scenarios

### Scenario 1: Clean startup
```
GIVEN Docker and Docker Compose v2 are installed
AND the deploy/ directory exists with all required files
WHEN running `docker compose up -d` from deploy/
THEN both services reach "running" state within 60 seconds
AND `docker compose ps` shows mosquitto and nodered as healthy/running
AND port 1883 is listening on the host
AND port 1880 is listening on the host
```

### Scenario 2: Mosquitto accepts MQTT connections
```
GIVEN both containers are running
WHEN an MQTT client connects to localhost:1883 without credentials
THEN the connection succeeds
AND the client can publish to topic "test/topic"
AND the client can subscribe to topic "test/topic"
AND published messages are received by subscribers
```

### Scenario 3: Node-RED connects to Mosquitto internally
```
GIVEN both containers are running
WHEN a Node-RED MQTT node is configured with broker host "mosquitto" and port 1883
THEN the connection status shows "connected"
AND Node-RED can publish to MQTT topics
AND Node-RED can receive messages from MQTT topics
```

### Scenario 4: Flow persistence across restart
```
GIVEN a flow exists in Node-RED (deployed and saved)
AND deploy/nodered/data/flows.json contains the flow definition
WHEN running `docker compose down`
THEN deploy/nodered/data/flows.json still exists on the host filesystem
WHEN running `docker compose up -d`
THEN the flow is still present in Node-RED editor
AND no flow data was lost
```

### Scenario 5: Required nodes available in palette
```
GIVEN Node-RED container is running
WHEN opening http://localhost:1880 in a browser
AND opening the node palette sidebar
THEN "dashboard" nodes are available (ui_button, ui_text, ui_gauge, etc.)
THEN "tfjs-coco-ssd" node is available
THEN "email" nodes are available (e-mail, e-mail in)
THEN "telegrambot" nodes are available
```

### Scenario 6: Stop does not delete bind mount data
```
GIVEN deploy/nodered/data/ contains flows.json and settings.js
WHEN running `docker compose down`
THEN deploy/nodered/data/flows.json still exists
AND deploy/nodered/data/settings.js still exists
AND the deploy/nodered/data/ directory is not empty
```

### Scenario 7: Mosquitto config is read-only
```
GIVEN the mosquitto container is running
WHEN inspecting the container mounts
THEN mosquitto.conf is mounted with read-only flag (:ro)
```

### Scenario 8: Docker Compose down preserves named volumes
```
GIVEN both services are running with data in Mosquitto
WHEN running `docker compose down`
THEN the named volumes mosquitto_data and mosquitto_logs still exist
WHEN running `docker compose down -v`
THEN the named volumes are removed (documented behavior)
```

---

## Verification Commands

```bash
# 1. Check structure
ls -R deploy/

# 2. Start services
cd deploy && docker compose up -d

# 3. Check services running
docker compose ps

# 4. Test Mosquitto connectivity
docker run --rm --network deploy_default eclipse-mosquitto mosquitto_sub -h mosquitto -t 'test' -C 1 -W 5

# 5. Test Node-RED HTTP
curl -s -o /dev/null -w "%{http_code}" http://localhost:1880
# Expected: 200 or 302

# 6. Check installed nodes in Node-RED
docker exec deploy-nodered-1 npm ls --depth=0 2>/dev/null | grep -E "node-red-dashboard|tfjs-coco-ssd|node-email|telegrambot"

# 7. Test persistence
touch deploy/nodered/data/test_persistence
docker compose down
test -f deploy/nodered/data/test_persistence && echo "PERSISTENCE OK" || echo "PERSISTENCE FAILED"
rm deploy/nodered/data/test_persistence

# 8. Check README exists
test -f deploy/README.md && echo "README OK" || echo "README MISSING"
```
