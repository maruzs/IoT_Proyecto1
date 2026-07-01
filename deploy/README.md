# SmartHome IoT Infrastructure — Docker Compose

Docker Compose infrastructure for the SmartHome IoT project. Runs a Mosquitto MQTT broker, Node-RED dashboard, backend services, LLM gateway, InfluxDB, Grafana, CoAP bridge, and MQTT-to-InfluxDB ingestion in isolated containers.

## Prerequisites

- **Docker** v24+ installed and running
- **Docker Compose** v2+ (verify with `docker compose version`)
- Minimum **512MB RAM** available for containers
- Ports **1880**, **8883**, and **1884** available on the host

## Quick Start

```bash
# 1. Configurar credenciales
cp deploy/.env.example deploy/.env
# Editar deploy/.env con tus valores reales

# 2. Levantar servicios (certificados TLS se generan en el build)
cd deploy
docker compose up -d

# 3. Verificar estado
docker compose ps

# 4. Ver logs
docker compose logs -f

# 5. Detener (conserva datos)
docker compose down
```

## Access

| Service | URL | Auth | Description |
|---------|-----|------|-------------|
| Node-RED | http://localhost:1880 | — | Visual flow editor y dashboard |
| Mosquitto (TLS) | mqtts://localhost:8883 | TLS + user/password | Servicios internos (backend, Node-RED) |
| Mosquitto (plain) | mqtt://localhost:1884 | user/password | Placas embebidas (MKR1000, ESP32-CAM) |
| MQTT to InfluxDB | — (internal) | user/password | Subscribe MQTT `smarthome/equipo69/#` y escribe en InfluxDB |

## Persistence

Two persistence strategies are used:

- **Node-RED flows** — bind mount `./nodered/data:/data`. Flows, credentials, and settings are stored as files on the host at `deploy/nodered/data/`. These survive `docker compose down` and are directly editable.
- **Mosquitto data** — named volumes `mosquitto_data` and `mosquitto_logs`. Broker persistence and logs are managed by Docker. These survive `docker compose down` but are removed by `docker compose down -v`.

> **Warning**: `docker compose down -v` removes all named volumes. Only use this when you want a clean slate.

## Certificate Management

Los certificados TLS se generan automaticamente durante `docker compose up -d` (etapa `cert-builder` del Dockerfile multi-stage de Mosquitto). **No es necesario ejecutar `generate-certs.sh` manualmente.**

**Flujo cuando un compañero clona el repo por primera vez:**

```bash
# 1. Clonar y levantar servicios (genera certificados nuevos)
cd deploy
docker compose up -d

# 2. Sincronizar CA cert con el firmware de la ESP32-CAM
./scripts/sync-ca-to-firmware.sh

# 3. Flashear la ESP32-CAM con el nuevo CA cert
arduino-cli upload -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32cam src/esp32cam_firmware/
```

**Cuando se regeneran los certificados** (`docker compose down && docker volume rm deploy_mosquitto_certs && docker compose up -d`):
- Volver a ejecutar `./scripts/sync-ca-to-firmware.sh`
- Re-flashear la ESP32-CAM

> **¿Por qué?** El CA cert está embebido en `src/esp32cam_firmware/src/secrets.h`. Si el certificado del broker cambia, el firmware debe actualizarse. El script `sync-ca-to-firmware.sh` automatiza la extracción desde el volumen Docker.

- **Servicios internos** (backend Python, Node-RED): usan TLS en puerto 8883 con validacion de CA.
- **MKR1000**: usa puerto 1884 sin TLS. No necesita este paso.
- **Seguridad**: Los certificados viven en un volumen Docker (`mosquitto_certs`), no en el repositorio. `secrets.h` está en `.gitignore`.

## Resource Requirements

| Service | Minimum RAM | Notes |
|---------|-------------|-------|
| Mosquitto | ~64MB | Lightweight MQTT broker |
| Node-RED | ~256MB+ | Increases with installed nodes and flow complexity |

## Troubleshooting

### Port already in use

If port 1880, 8883, or 1884 is occupied:

```bash
# Find what is using the port
sudo lsof -i :1880
sudo lsof -i :8883
sudo lsof -i :1884

# Or change the host port in docker-compose.yml
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

> **NOTE**: If you modify `entrypoint.sh` or `acl.conf`, rebuild the mosquitto image: `docker compose up -d --build mosquitto`. These files are COPY'd at build time, not bind-mounted.

### Verify services are running

```bash
# Both services should show "running"
docker compose ps

# Mosquitto should show "healthy" after ~15 seconds
docker compose ps mosquitto

# Test MQTT TLS (servicios internos, puerto 8883)
docker run --rm --network host -v deploy_mosquitto_certs:/certs:ro \
  eclipse-mosquitto:2 mosquitto_pub -h localhost -p 8883 \
  --cafile /certs/ca.crt -u iot_user -P change_me_before_deploy \
  -t "test/topic" -m "hello"

# Test MQTT plain (placas, puerto 1884)
docker run --rm --network host eclipse-mosquitto:2 mosquitto_pub \
  -h localhost -p 1884 -u iot_user -P change_me_before_deploy \
  -t "test/topic" -m "hello"

# Test Node-RED HTTP endpoint
curl -s -o /dev/null -w "%{http_code}" http://localhost:1880
# Expected: 200 or 302
```

## Firmware Deployment (Placas)

Las placas NO usan TLS. Solo necesitan WiFi + credenciales MQTT.

### 1. Configurar credenciales

```bash
# Crear secrets.h desde el template para cada placa
cp src/mkr1000_firmware/src/secrets.h.example src/mkr1000_firmware/src/secrets.h
cp src/esp32cam_firmware/src/secrets.h.example src/esp32cam_firmware/src/secrets.h

# Editar ambos secrets.h con WiFi y MQTT reales:
#   WIFI_SSID, WIFI_PASSWORD, MQTT_SERVER, MQTT_USER, MQTT_PASSWORD
#   MQTT_PORT debe ser 1884 (sin TLS)
```

### 2. Compilar y flashear

```bash
# MKR1000
arduino-cli compile --fqbn arduino:samd:mkr1000 src/mkr1000_firmware/
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:samd:mkr1000 src/mkr1000_firmware/

# ESP32-CAM
arduino-cli compile --fqbn esp32:esp32:esp32cam src/esp32cam_firmware/
arduino-cli upload -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32cam src/esp32cam_firmware/
```

### 3. Verificar conexion

```bash
# Datos del MKR1000 (publica cada 2 segundos)
docker run --rm --network host eclipse-mosquitto:2 mosquitto_sub \
  -h IP_DEL_BROKER -p 1884 -u iot_user -P tu_password \
  -t 'smarthome/equipo69/datos' -C 2 -W 10

# Evento de camara del ESP32-CAM
docker run --rm --network host eclipse-mosquitto:2 mosquitto_sub \
  -h IP_DEL_BROKER -p 1884 -u iot_user -P tu_password \
  -t 'smarthome/equipo69/camara/evento' -C 1 -W 10
```

> **NOTA**: Si rotas credenciales MQTT, solo cambia `MQTT_USER`/`MQTT_PASSWORD` en `secrets.h` y re-flashea. No necesitas tocar certificados.

## Pre-installed Node-RED Nodes

The Node-RED image includes these nodes at build time:

- **node-red-dashboard** — UI widgets (buttons, gauges, charts)
- **node-red-contrib-tfjs-coco-ssd** — TensorFlow.js object detection (ESP32-CAM)
- **node-red-node-email** — Email notifications
- **node-red-contrib-telegrambot** — Telegram bot integration
