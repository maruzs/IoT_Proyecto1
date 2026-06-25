import json
import logging
import random
import time
import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# MQTT settings for local host testing
import os
MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1884"))  # Plain port exposed on host
MQTT_USER = os.environ.get("MQTT_USER", "mkr1000-equipo69")
MQTT_PASS = os.environ.get("MQTT_PASSWORD", "IoT2026Secure!")
EQUIPO_ID = os.environ.get("EQUIPO_ID", "equipo69")

TOPIC_DATOS = f"smarthome/{EQUIPO_ID}/datos"
TOPIC_MOVIMIENTO = f"smarthome/{EQUIPO_ID}/movimiento"


def main():
    client = mqtt.Client(client_id="mock-telemetry-feeder")
    client.username_pw_set(MQTT_USER, MQTT_PASS)

    logger.info("Connecting to local Mosquitto at %s:%d...", MQTT_BROKER, MQTT_PORT)
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    except Exception as e:
        logger.error("Could not connect to MQTT broker: %s. Is docker compose-light running?", e)
        return

    client.loop_start()

    temp = 22.0
    hum = 55.0
    gas = 280.0
    logger.info("Mock telemetry feeder running. Publishing to %s...", TOPIC_DATOS)

    try:
        step = 0
        while True:
            # Simulate a slow drift up/down
            # Let's slowly increase temp and gas to see linear regression trend in action
            temp += random.uniform(-0.05, 0.15)
            hum += random.uniform(-0.2, 0.15)
            gas += random.uniform(-1.0, 3.5)

            # Constrain to realistic values
            temp = max(15.0, min(38.0, temp))
            hum = max(30.0, min(90.0, hum))
            gas = max(100.0, min(600.0, gas))

            payload_datos = {
                "equipo": EQUIPO_ID,
                "temperatura": round(temp, 2),
                "humedad": round(hum, 2),
                "gas": round(gas, 2),
                "gas_digital": "ALERTA" if gas > 400 else "NORMAL",
                "sensor_extra": round(random.uniform(20.0, 50.0), 1),
            }

            client.publish(TOPIC_DATOS, json.dumps(payload_datos), qos=0)
            logger.info("Published sensor readings: Temp=%.2f, Hum=%.2f, Gas=%.2f", temp, hum, gas)

            # Publish motion every 10 seconds
            if step % 5 == 0:
                movimiento = random.choice([True, False])
                client.publish(TOPIC_MOVIMIENTO, "true" if movimiento else "false", qos=0)
                logger.info("Published motion state: %s", movimiento)

            step += 1
            time.sleep(2.0)
    except KeyboardInterrupt:
        logger.info("Mock feeder stopping...")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
