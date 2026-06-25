import json
import logging
import urllib.request
import urllib.parse
import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Config
import os
MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1884"))
MQTT_USER = os.environ.get("MQTT_USER", "digital-twin-equipo69")
MQTT_PASS = os.environ.get("MQTT_PASSWORD", "IoT2026Secure!")
EQUIPO_ID = os.environ.get("EQUIPO_ID", "equipo69")

INFLUX_URL = os.environ.get("INFLUX_URL", "http://localhost:8086/api/v2/write?org=smarthome&bucket=sensores&precision=s")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN", "myinfluxadmintoken123")

TOPIC_BASE = f"smarthome/{EQUIPO_ID}"


def write_to_influx(line_protocol: str) -> None:
    """Send line protocol data to InfluxDB 2.x via raw HTTP POST request."""
    req = urllib.request.Request(
        INFLUX_URL,
        data=line_protocol.encode("utf-8"),
        headers={
            "Authorization": f"Token {INFLUX_TOKEN}",
            "Content-Type": "text/plain; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as response:
            if response.status not in (204, 200):
                logger.warning("InfluxDB write status: %d", response.status)
    except Exception as e:
        logger.error("Failed to write to InfluxDB: %s", e)


def _on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT. Subscribing to %s/#...", TOPIC_BASE)
        client.subscribe(f"{TOPIC_BASE}/#")
    else:
        logger.error("MQTT connection failed, rc=%d", rc)


def _on_message(client, userdata, msg):
    topic = msg.topic
    suffix = topic[len(TOPIC_BASE) + 1 :]
    payload_str = msg.payload.decode("utf-8").strip()

    try:
        # 1. Telemetry Data
        if suffix == "datos":
            data = json.loads(payload_str)
            temp = data.get("temperatura")
            hum = data.get("humedad")
            gas = data.get("gas")
            extra = data.get("sensor_extra")

            fields = []
            if temp is not None:
                fields.append(f"temperatura={temp}")
            if hum is not None:
                fields.append(f"humedad={hum}")
            if gas is not None:
                fields.append(f"gas={gas}")
            if extra is not None:
                fields.append(f"sensor_extra={extra}")

            if fields:
                line = f"sensor_data,equipo={EQUIPO_ID} {','.join(fields)}"
                logger.info("Ingesting telemetry to InfluxDB: %s", line)
                write_to_influx(line)

        # 2. Prediction Topics: e.g. prediccion/temperatura
        elif suffix.startswith("prediccion/"):
            metric = suffix.split("/")[-1]
            data = json.loads(payload_str)
            val = data.get("valor")
            if val is not None:
                line = f"sensor_predictions,equipo={EQUIPO_ID} {metric}={val}"
                logger.info("Ingesting prediction to InfluxDB: %s", line)
                write_to_influx(line)

    except Exception as e:
        logger.error("Error processing topic %s: %s", topic, e)


def main():
    client = mqtt.Client(client_id="mqtt-to-influx-bridge")
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = _on_connect
    client.on_message = _on_message

    logger.info("Starting bridge, connecting to local Mosquitto at %s:%d...", MQTT_BROKER, MQTT_PORT)
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    except Exception as e:
        logger.error("MQTT connection failed: %s. Is compose stack running?", e)
        return

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Bridge stopping...")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
