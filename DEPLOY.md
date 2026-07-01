# Deploy Guide — SmartHome IoT Project

Guía de despliegue rápido para la presentación. Cubre Docker, placas, verificación y plan B si el MKR1000 falla.

---

## Índice

1. [Requisitos](#1-requisitos)
2. [Levantar infraestructura Docker](#2-levantar-infraestructura-docker)
3. [Firmware de las placas](#3-firmware-de-las-placas)
4. [Verificación rápida pre-demo](#4-verificación-rápida-pre-demo)
5. [Plan B: MKR1000 sin WiFi](#5-plan-b-mkr1000-sin-wifi)
6. [Orden de la demo](#6-orden-de-la-demo)
7. [Checklist pre-presentación](#7-checklist-pre-presentación)
8. [Script de emergencia (mock data)](#8-script-de-emergencia-mock-data)

---

## 1. Requisitos

| Herramienta | Versión | Verificar |
|-------------|---------|-----------|
| Docker + Docker Compose | > 20.x | `docker --version` |
| arduino-cli | cualquier | `arduino-cli version` |
| mosquitto_pub/sub | cualquier | `mosquitto_sub -h` |
| curl | cualquier | `curl --version` |
| python3 | > 3.10 | `python3 --version` |

Puertos requeridos libres:

| Puerto | Servicio |
|--------|----------|
| 8883 | Mosquitto TLS |
| 1884 | Mosquitto no-TLS (MKR1000) |
| 8000 | Backend (face recognition) |
| 8001 | LLM Gateway |
| 8002 | MCP Server (TLS) |
| 8003 | Digital Twin |
| 8086 | InfluxDB |
| 3000 | Grafana |
| 1880 | Node-RED |
| 80 | Frontend (nginx) |
| 11434 | Ollama |

---

## 2. Levantar infraestructura Docker

```bash
# Desde la raíz del proyecto
cd /home/lambda/UwU/Iot/Proy1/IoT_Proyecto1

# Levantar TODO el stack
docker compose -f deploy/docker-compose.yml up -d

# Verificar que los 12 servicios estén UP
docker compose -f deploy/docker-compose.yml ps
```

Salida esperada:

```
deploy-backend-1          Up
deploy-coap-bridge-1      Up
deploy-digital-twin-1     Up
deploy-frontend-1         Up
deploy-grafana-1          Up
deploy-influxdb-1         Up
deploy-llm-gateway-1      Up
deploy-mcp-server-1       Up
deploy-mosquitto-1        Up (healthy)
deploy-mqtt-to-influx-1   Up
deploy-nodered-1          Up (healthy)
deploy-ollama-1           Up
```

Si algún servicio no levanta, revisar logs:

```bash
docker logs <nombre-servicio> --tail 20
```

---

## 3. Firmware de las placas

### 3.1 Detectar placas conectadas

```bash
arduino-cli board list
```

Salida esperada:

```
/dev/ttyACM0   Arduino MKR 1000 WiFi    arduino:samd:mkr1000
/dev/ttyUSB0   Unknown                  (ESP32-CAM — correcto)
```

### 3.2 Compilar y flashear

```bash
# Opción 1: firmware-tool.sh (recomendado — genera secrets desde .env)
./deploy/scripts/firmware-tool.sh build
./deploy/scripts/firmware-tool.sh upload

# Opción 2: flash.sh directo (compila + flashea automático)
bash deploy/boards/flash.sh

# Opción 3: manual (solo flashear, sin recompilar)
bash deploy/boards/flash.sh --no-compile
```

### 3.3 Flashear solo ESP32-CAM (más rápido)

```bash
arduino-cli compile --fqbn esp32:esp32:esp32cam src/esp32cam_firmware/
arduino-cli upload -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32cam src/esp32cam_firmware/
```

### 3.4 Reset manual post-flash

Si después del flash la ESP32-CAM queda en **modo download** (no responde):

```bash
python3 -c "
import serial, time
ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=2)
ser.setDTR(False)   # GPIO0 HIGH (boot normal)
ser.setRTS(True)    # EN LOW (reset)
time.sleep(0.3)
ser.setRTS(False)   # EN HIGH (run)
ser.close()
print('Reset enviado — modo boot normal')
"
```

O directamente: **desconectar y reconectar el USB** de la ESP32-CAM.

---

## 4. Verificación rápida pre-demo

```bash
# 1. Contenedores
docker ps --format "table {{.Names}}\t{{.Status}}"

# 2. Datos de sensores fluyendo (debe mostrar temp actualizada)
curl -s http://localhost:8003/gemelo/estado | python3 -c "
import sys,json;d=json.load(sys.stdin);e=d['estado_actual']
print(f'🌡️ {e[\"temperatura\"]}°C  💧 {e[\"humedad\"]}%  🔥 {e[\"gas\"]}ppm')
print(f'📊 Historial: {len(d[\"historial_1h\"])} entradas')
print(f'🕐 Último update: {d[\"ultimo_update\"]}')
"

# 3. LLM Gateway
curl -s http://localhost:8001/health
# {"status":"healthy","ollama":"connected","mqtt":"connected"}

# 4. MCP Server
curl -sk -X POST https://localhost:8002/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
# Debe listar 9 tools registradas

# 5. Frontend
curl -so /dev/null -w "Frontend: HTTP %{http_code}\n" http://localhost/

# 6. Grafana
curl -so /dev/null -w "Grafana: HTTP %{http_code}\n" http://localhost:3000/

# 7. InfluxDB
curl -s http://localhost:8086/health | python3 -c "import sys,json;print(json.load(sys.stdin)['message'])"
# "ready for queries and writes"

# 8. Clientes MQTT activos (debe ser 9)
docker exec deploy-mosquitto-1 mosquitto_sub -h localhost -p 1883 \
  -t '$SYS/broker/clients/active' -C 1 -W 3
```

---

## 5. Plan B: MKR1000 sin WiFi

El MKR1000 con librería `WiFi101` es sensible a:

- Distancia del AP — mantener a < 5m del router
- Interferencia — evitar microondas, monitores bebé cerca
- Fuente de alimentación — USB directo a la PC, no hubs

Si el MKR1000 **no conecta WiFi**, el sistema sigue funcionando completamente con datos simulados.

### Opción A: Script de mock data (recomendado)

```bash
# Publica datos falsos cada 2s en el mismo tópico que el MKR1000
bash deploy/scripts/mock-mkr1000.sh
```

Esto publica en `smarthome/equipo69/datos`. El Digital Twin lo recibe igual,
y todo el pipeline (DT → InfluxDB → Grafana → MCP → LangGraph) funciona idéntico.

### Opción B: DEV_LOCAL mode (simulación interna del DT)

El Digital Twin tiene un modo `DEV_LOCAL` que genera datos ficticios automáticamente:

```yaml
# En docker-compose.yml, en el servicio digital-twin:
environment:
  - MODE=DEV_LOCAL
  - CONSOLIDATION_INTERVAL=5   # cada 5s en vez de 60s
  - PREDICTION_INTERVAL=15     # cada 15s en vez de 600s
```

Luego recrear:

```bash
docker compose -f deploy/docker-compose.yml up -d digital-twin
```

### Opción C: Publicación manual con mosquitto_pub

```bash
# Un solo dato
mosquitto_pub -h localhost -p 8883 --cafile deploy/mosquitto/certs/ca.crt \
  -u mkr1000-equipo69 -P test123 \
  -t "smarthome/equipo69/datos" \
  -m '{"equipo":"equipo69","temperatura":25.5,"humedad":60,"gas":350,"gas_digital":"NORMAL","sensor_extra":30}'
```

---

## 6. Orden de la demo

```
1. Abrir Frontend → http://localhost/
   → Mostrar sección "Agente" (chat)
   → Mostrar sección "Reconocimiento" (cámara)

2. Preguntar al agente:
   → "¿cómo está la temperatura?"
     (usa MCP → Digital Twin → get_sensor_state)
   → "cual fue la temperatura en la última hora?"
     (usa MCP → Digital Twin → query_history)

3. Mostrar Grafana → http://localhost:3000 (admin/admin)
   → Dashboards de sensores (temp, hum, gas)
   → Panel de predicciones (línea sólida + punteada)
   → Alertas configuradas (temp > 28°C, gas > 400ppm)

4. Acciones desde el chat:
   → "enciende la luz de alerta"
     (MCP → Node-RED → MQTT → LED)
   → "/silenciar"
     (MCP → Node-RED → silence_alerts)
   → "activa la cámara 3 segundos"
     (MCP → Node-RED → MQTT → ESP32-CAM burst)

5. Mostrar Node-RED → http://localhost:1880
   → Flujos: T-018 alertas (cooldown, notificacion)
   → Endpoints REST: /api/sensors, /api/status, /api/alerts/silence

6. Cierre técnico:
   → Mencionar que el LLM (phi3:mini) corre 100% local en CPU
   → Toda la comunicación es TLS (Mosquitto 8883)
   → Arquitectura: Firmware → MQTT → DT → MCP → LangGraph → Node-RED
```

---

## 7. Checklist pre-presentación

```bash
echo "=== CHECKLIST PRE-DEMO ==="
echo ""

echo -n "🐳 12 contenedores UP: "
docker ps --format '{{.Names}}' | wc -l

echo -n "🌡️  Sensor data fluyendo: "
curl -s http://localhost:8003/gemelo/estado | python3 -c "
import sys,json;d=json.load(sys.stdin)
e=d['estado_actual']
print(f'{e[\"temperatura\"]}°C / {e[\"humedad\"]}% / {e[\"gas\"]}ppm')
" 2>/dev/null || echo "❌ REVISAR"

echo -n "📷 ESP32-CAM: "
ls /dev/ttyUSB0 2>/dev/null && echo "conectada" || echo "no detectada"

echo -n "🤖 LLM Gateway: "
curl -so /dev/null -w "%{http_code}" http://localhost:8001/health 2>/dev/null || echo "❌"

echo -n "📈 Grafana: "
curl -so /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null || echo "❌"

echo -n "🌐 Frontend: "
curl -so /dev/null -w "%{http_code}" http://localhost/ 2>/dev/null || echo "❌"

echo ""
echo "=== Plan B listo ==="
echo "Mock script:  bash deploy/scripts/mock-mkr1000.sh  (en otro terminal)"
```

---

## 8. Script de emergencia (mock data)

Si el MKR1000 falla, correr en un terminal separado durante la demo:

```bash
#!/usr/bin/env bash
# mock-mkr1000.sh — Publica datos falsos cada 2s como si fuera el MKR1000
# Útil para la presentación cuando la placa no conecta WiFi.
# Correr en un terminal separado: bash deploy/scripts/mock-mkr1000.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CERTS="${PROJECT_ROOT}/deploy/mosquitto/certs/ca.crt"
BROKER="localhost"
PORT=8883
USER="mkr1000-equipo69"
PASS="test123"
EQUIPO="equipo69"

echo "=== Mock MKR1000 iniciado ==="
echo "Publicando datos cada 2s en smarthome/${EQUIPO}/datos"
echo "Presioná Ctrl+C para detener"
echo ""

while true; do
  TEMP=$(printf "%.1f" "$(echo "scale=1; 20 + ($RANDOM % 200) / 10" | bc)")
  HUM=$(printf "%.1f" "$(echo "scale=1; 50 + ($RANDOM % 300) / 10" | bc)")
  GAS=$(printf "%.0f" "$(echo "scale=0; 280 + ($RANDOM % 300)" | bc)")
  SOUND=$(printf "%.0f" "$(echo "scale=0; 20 + ($RANDOM % 60)" | bc)")

  mosquitto_pub -h "$BROKER" -p "$PORT" --cafile "$CERTS" \
    -u "$USER" -P "$PASS" \
    -t "smarthome/${EQUIPO}/datos" \
    -m "{\"equipo\":\"${EQUIPO}\",\"temperatura\":${TEMP},\"humedad\":${HUM},\"gas\":${GAS},\"gas_digital\":\"NORMAL\",\"sensor_extra\":${SOUND}}"

  echo "$(date +%H:%M:%S)  temp=${TEMP}°C  hum=${HUM}%  gas=${GAS}ppm  sound=${SOUND}"
  sleep 2
done
```

---

## Referencias rápidas

| Qué | Comando |
|-----|---------|
| Logs de un servicio | `docker logs deploy-<nombre>-1 --tail 20` |
| Reset ESP32-CAM | `python3 -c "import serial,time;ser=serial.Serial('/dev/ttyUSB0',115200);ser.setDTR(0);ser.setRTS(1);time.sleep(.3);ser.setRTS(0)"` |
| Ver data del DT | `curl -s localhost:8003/gemelo/estado \| python3 -m json.tool` |
| Probar LLM query | `curl -s --max-time 120 -X POST localhost:8001/llm/query -H 'Content-Type: application/json' -d '{"prompt":"decime el estado"}'` |
| Probar agente | `curl -s --max-time 120 -X POST localhost:8001/llm/agent -H 'Content-Type: application/json' -d '{"message":"¿cómo está la temperatura?"}'` |
| Subscribir a datos | `mosquitto_sub -h localhost -p 8883 --cafile deploy/mosquitto/certs/ca.crt -u digital-twin-equipo69 -P test123 -t 'smarthome/equipo69/#'` |
| Forzar burst cámara | `mosquitto_pub -h localhost -p 8883 --cafile deploy/mosquitto/certs/ca.crt -u nodered-smarthome -P test123 -t "smarthome/equipo69/camara/captura" -m '{"accion":"iniciar_burst","duracion":3}'` |
