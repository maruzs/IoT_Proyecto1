# =============================================================================
# Mosquitto multistage — genera certificados TLS en el build
# =============================================================================

# Stage 1: Generar PKI + passwd
FROM alpine:3 AS cert-builder
RUN apk add --no-cache openssl mosquitto

ARG MQTT_BROKER_IP=127.0.0.1

WORKDIR /certs

RUN openssl genrsa -out ca.key 2048 \
    && openssl req -new -x509 -days 365 -key ca.key -out ca.crt \
        -subj "/C=AR/O=SmartHomeIoT/CN=SmartHomeIoT-CA" \
    && openssl genrsa -out server.key 2048 \
    && openssl req -new -key server.key -out /tmp/server.csr \
        -subj "/C=AR/O=SmartHomeIoT/CN=mosquitto" \
    && printf "subjectAltName=DNS:mosquitto,DNS:localhost,IP:127.0.0.1,IP:${MQTT_BROKER_IP}" > /tmp/san.ext \
    && openssl x509 -req -in /tmp/server.csr \
        -CA ca.crt -CAkey ca.key -CAcreateserial \
        -out server.crt -days 365 -extfile /tmp/san.ext \
    && chmod 644 ca.crt ca.key server.crt server.key

# Stage 2: Imagen final de Mosquitto
FROM eclipse-mosquitto:2

COPY --from=cert-builder /certs/ /mosquitto/certs/
COPY --from=cert-builder /certs/ca.crt /ca.crt

# ponytail: acl.conf and entrypoint.sh are COPY'd at build time, not bind-mounted.
#          If you modify them, run: docker compose up -d --build mosquitto
COPY deploy/mosquitto/config/mosquitto.conf /mosquitto/config/mosquitto.conf
COPY deploy/mosquitto/config/acl.conf /mosquitto/config/acl.conf
COPY deploy/mosquitto/config/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8883
EXPOSE 1884

ENTRYPOINT ["/entrypoint.sh"]
