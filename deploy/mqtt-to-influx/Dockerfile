# =============================================================================
# Multistage: influx CLI (Stage 1) + Python runtime (Stage 2)
# =============================================================================

# Stage 1: influx CLI for retention policy management
FROM influxdb:2.7 AS influx-cli

# Stage 2: Python runtime
FROM python:3.11-slim

WORKDIR /app

# Copy influx CLI and entrypoint
COPY --from=influx-cli /usr/local/bin/influx /usr/local/bin/influx
COPY deploy/mqtt-to-influx/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Install Python dependency
RUN pip install --no-cache-dir paho-mqtt

# Copy application
COPY src/digital_twin/mqtt_to_influx.py .

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/entrypoint.sh"]
