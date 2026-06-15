# SmartHome IoT Infrastructure — Docker Compose

Docker Compose infrastructure for the SmartHome IoT project. Runs a Mosquitto MQTT broker and Node-RED dashboard in isolated containers.

## Prerequisites

- **Docker** v24+ installed and running
- **Docker Compose** v2+ (comes bundled with Docker Desktop; verify with `docker compose version`)
- **OpenSSL** installed (required for certificate generation)
- Minimum **512MB RAM** available for containers
- Ports **1880** and **8883** available on the host

## Quick Start

```bash
# 1. Generate TLS certificates and Mosquitto password file
cd deploy
export MQTT_USER=iot_user
export MQTT_PASSWORD=change_me_before_deploy
./scripts/generate-certs.sh

# 2. Start both services in the background
docker compose up -d

# 3. Check service status
docker compose ps

# 4. View logs
docker compose logs -f

# 5. Stop services (preserves all data)
docker compose down
```

## Access

| Service | URL | Description |
|---------|-----|-------------|
| Node-RED | http://localhost:1880 | Visual flow editor and dashboard |
| Mosquitto | mqtts://localhost:8883 | MQTT broker (TLS + auth required) |

## Persistence

Two persistence strategies are used:

- **Node-RED flows** — bind mount `./nodered/data:/data`. Flows, credentials, and settings are stored as files on the host at `deploy/nodered/data/`. These survive `docker compose down` and are directly editable.
- **Mosquitto data** — named volumes `mosquitto_data` and `mosquitto_logs`. Broker persistence and logs are managed by Docker. These survive `docker compose down` but are removed by `docker compose down -v`.

> **Warning**: `docker compose down -v` removes all named volumes. Only use this when you want a clean slate.

## Certificate Management

Certificates are generated once via `generate-certs.sh` and stored in `deploy/mosquitto/certs/`:

- **Renewal**: Re-run `generate-certs.sh` with the same or new credentials, then restart containers with `docker compose restart`.
- **CA changes**: If the CA certificate is regenerated, all firmware devices (MKR1000 and ESP32-CAM) must be re-flashed with the new `CA_CERT` value from `secrets.h`.
- **Security**: Private keys (`*.key`) and the password file (`passwd`) must NEVER be committed to git. They are already listed in `.gitignore`.

## Resource Requirements

| Service | Minimum RAM | Notes |
|---------|-------------|-------|
| Mosquitto | ~64MB | Lightweight MQTT broker |
| Node-RED | ~256MB+ | Increases with installed nodes and flow complexity |

## Troubleshooting

### Port already in use

If port 1880 or 8883 is occupied:

```bash
# Find what is using the port
sudo lsof -i :1880
sudo lsof -i :8883

# Or change the host port in docker-compose.yml
# e.g., "11880:1880" to access Node-RED at http://localhost:11880
```

### Permission denied on bind mount

If Node-RED cannot write to `./nodered/data/`:

```bash
# Fix ownership (Node-RED runs as UID 1000 inside the container)
sudo chown -R 1000:1000 deploy/nodered/data/
```

### Mosquitto not healthy

If `docker compose ps` shows mosquitto as `unhealthy`:

```bash
# Check mosquitto logs
docker compose logs mosquitto

# Verify config is mounted correctly
docker inspect deploy-mosquitto-1 | grep -A5 Mounts

# Verify certificates exist
ls -la deploy/mosquitto/certs/
cat deploy/mosquitto/config/passwd
```

If the container exits immediately, ensure you ran `./scripts/generate-certs.sh` before `docker compose up -d`.

### Verify services are running

```bash
# Both services should show "running"
docker compose ps

# Mosquitto should show "healthy" after ~15 seconds
docker compose ps mosquitto

# Test MQTT connection over TLS with credentials (requires mosquitto-clients)
mosquitto_pub -h localhost -p 8883 \
  --cafile deploy/mosquitto/certs/ca.crt \
  -u iot_user -P change_me_before_deploy \
  -t "test/topic" -m "hello"

# Test Node-RED HTTP endpoint
curl -s -o /dev/null -w "%{http_code}" http://localhost:1880
# Expected: 200 or 302
```

## Pre-installed Node-RED Nodes

The Node-RED image includes these nodes at build time:

- **node-red-dashboard** — UI widgets (buttons, gauges, charts)
- **node-red-contrib-tfjs-coco-ssd** — TensorFlow.js object detection (ESP32-CAM)
- **node-red-node-email** — Email notifications
- **node-red-contrib-telegrambot** — Telegram bot integration
