FROM alpine:3.21 AS certbuilder
RUN apk add --no-cache openssl && \
    mkdir -p /certs && \
    openssl genrsa -out /certs/ca.key 2048 && \
    openssl req -new -x509 -days 365 -key /certs/ca.key -out /certs/ca.crt \
        -subj "/C=AR/O=SmartHomeIoT/CN=SmartHomeIoT-CA" && \
    openssl genrsa -out /certs/server.key 2048 && \
    openssl req -new -key /certs/server.key -out /certs/server.csr \
        -subj "/C=AR/O=SmartHomeIoT/CN=mosquitto" && \
    openssl x509 -req -days 365 -in /certs/server.csr -CA /certs/ca.crt -CAkey /certs/ca.key \
        -CAcreateserial -out /certs/server.crt

FROM eclipse-mosquitto:2
COPY --from=certbuilder /certs/ca.crt /mosquitto/certs/ca.crt
COPY --from=certbuilder /certs/server.crt /mosquitto/certs/server.crt
COPY --from=certbuilder /certs/server.key /mosquitto/certs/server.key
COPY deploy/mosquitto/config/mosquitto.conf /mosquitto/config/mosquitto.conf
EXPOSE 8883
