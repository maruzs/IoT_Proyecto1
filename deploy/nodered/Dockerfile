# =============================================================================
# Node-RED SmartHome IoT — Multi-stage Dockerfile
# =============================================================================
# Stage 1: procesa templates (flows_cred + settings) con el token de Telegram.
# Stage 2: imagen final con Node-RED, config baked-in y entrypoint wrapper.
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1 — Config builder
# ---------------------------------------------------------------------------
FROM alpine:3.20 AS config
ARG TELEGRAM_BOT_TOKEN
ARG MQTT_USER=equipo69
ARG MQTT_PASSWORD=IoT2026Secure!
WORKDIR /tmp

# Generar flows_cred.json con credenciales reales
COPY deploy/nodered/flows_cred.json.template .
RUN sed -e "s/__TELEGRAM_BOT_TOKEN__/${TELEGRAM_BOT_TOKEN}/g" \
        -e "s/__MQTT_USER__/${MQTT_USER}/g" \
        -e "s/__MQTT_PASSWORD__/${MQTT_PASSWORD}/g" \
        flows_cred.json.template > flows_cred.json && \
    echo "[config] flows_cred.json generated"

# Copiar settings.js (ya tiene DNS fix + credentialSecret=false)
COPY deploy/nodered/settings.js.template settings.js

# ---------------------------------------------------------------------------
# Stage 2 — Node-RED final
# ---------------------------------------------------------------------------
FROM nodered/node-red:latest

USER root

# Instalar nodos extra (dashboard, Telegram, etc.)
RUN npm install --no-audit --no-fund \
    node-red-dashboard \
    node-red-contrib-tfjs-coco-ssd \
    node-red-node-email \
    node-red-contrib-telegrambot

# Directorio donde va la config baked-in
RUN mkdir -p /etc/nodered-staging

# Copiar archivos procesados del stage 1
COPY --from=config /tmp/flows_cred.json /etc/nodered-staging/
COPY --from=config /tmp/settings.js     /usr/src/node-red/.node-red/settings.js

# Copiar flows.json del repo
COPY nodered/flows.json /etc/nodered-staging/

# Entrypoint wrapper
COPY deploy/nodered/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER node-red
ENTRYPOINT ["/entrypoint.sh"]
