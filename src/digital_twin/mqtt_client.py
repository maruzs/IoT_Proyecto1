import json
import logging
import os
import ssl
from typing import Any
import paho.mqtt.client as mqtt
from .state_manager import StateManager

logger = logging.getLogger(__name__)


class DigitalTwinMQTTClient:
    """MQTT Client for the Digital Twin service.

    Subscribes to all team topics under 'smarthome/{equipo_id}/#' and updates
    the state manager with sensor readings and actuator states.
    Also handles publishing calculated predictions.
    """

    def __init__(self, state_manager: StateManager) -> None:
        self.state_manager = state_manager

        # Load environment variables
        self.broker = os.environ.get("MQTT_BROKER", "mosquitto")
        self.port = int(os.environ.get("MQTT_PORT", "8883"))
        self.user = os.environ.get("MQTT_USER", "equipo69")
        self.password = os.environ.get("MQTT_PASSWORD", "")
        self.equipo_id = os.environ.get("EQUIPO_ID", "equipo69")

        # TLS configuration
        self.tls_enabled = os.environ.get("MQTT_TLS", "true").lower() == "true"
        # Check both possible environment variables for CA certificate
        self.ca_cert_path = os.environ.get("MQTT_TLS_CA") or os.environ.get("MQTT_CA_CERT")

        self.topic_base = f"smarthome/{self.equipo_id}"

        # Initialize paho-mqtt client with v1/v2 compatibility
        try:
            self.client = mqtt.Client(client_id=f"digital-twin-{self.equipo_id}")
        except TypeError:
            self.client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION1,
                client_id=f"digital-twin-{self.equipo_id}",
            )

        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

    def connect(self) -> None:
        """Connect to the Mosquitto broker and start the background loop."""
        if self.tls_enabled:
            if self.ca_cert_path and os.path.exists(self.ca_cert_path):
                try:
                    context = ssl.create_default_context()
                    context.load_verify_locations(self.ca_cert_path)
                    # For self-signed dev certificates, disable hostname check if needed,
                    # but paho-mqtt's standard tls_set_context handles it.
                    self.client.tls_set_context(context)
                    logger.info("MQTT TLS enabled using CA cert: %s", self.ca_cert_path)
                except Exception as e:
                    logger.error("Failed to configure MQTT TLS context: %s", e)
            else:
                logger.warning(
                    "MQTT TLS is enabled but CA cert path '%s' does not exist. Connecting without TLS context.",
                    self.ca_cert_path,
                )

        if self.user:
            self.client.username_pw_set(self.user, self.password)

        logger.info("Connecting to MQTT broker at %s:%d...", self.broker, self.port)
        self.client.connect(self.broker, self.port)
        self.client.loop_start()

    def disconnect(self) -> None:
        """Stop background loop and disconnect cleanly."""
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("MQTT client disconnected cleanly")

    def publish_prediction(self, metric: str, value: float) -> None:
        """Publish a prediction value to `smarthome/{equipo_id}/prediccion/{metric}`."""
        topic = f"prediccion/{metric}"
        payload = {
            "valor": round(value, 2),
            "horizon_min": 30,
            "equipo": self.equipo_id,
        }
        full_topic = f"{self.topic_base}/{topic}"
        try:
            self.client.publish(full_topic, json.dumps(payload), qos=1)
            logger.info("Published prediction to MQTT: %s -> %s", full_topic, payload)
        except Exception as e:
            logger.error("Failed to publish prediction to MQTT topic %s: %s", full_topic, e)

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: dict, rc: int) -> None:
        if rc == 0:
            logger.info("MQTT Client connected successfully to %s:%d", self.broker, self.port)
            # Subscribe to all team topics
            subscribe_topic = f"{self.topic_base}/#"
            client.subscribe(subscribe_topic, qos=1)
            logger.info("Subscribed to wildcard topic: %s", subscribe_topic)
        else:
            logger.error("MQTT Connection failed with return code %d", rc)

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int) -> None:
        if rc == 0:
            logger.info("MQTT Client disconnected cleanly")
        else:
            logger.warning("MQTT Client disconnected unexpectedly (rc=%d), reconnecting...", rc)

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        topic = msg.topic
        logger.debug("Received MQTT message on topic: %s", topic)

        try:
            payload_str = msg.payload.decode("utf-8").strip()
        except UnicodeDecodeError:
            logger.warning("Received non-UTF-8 payload on topic: %s", topic)
            return

        # Check relative sub-topic
        suffix = topic[len(self.topic_base) + 1 :]

        try:
            # 1. Topic: datos (Consolidated sensor values)
            if suffix == "datos":
                data = json.loads(payload_str)
                temp = data.get("temperatura")
                hum = data.get("humedad")
                gas = data.get("gas")
                # Arduino MQ publishes sonido as sensor_extra
                sensor_extra = data.get("sensor_extra")

                self.state_manager.update_sensor_readings(
                    temp=float(temp) if temp is not None else None,
                    hum=float(hum) if hum is not None else None,
                    gas=float(gas) if gas is not None else None,
                    sensor_extra=float(sensor_extra) if sensor_extra is not None else None,
                )

                # If the payload has explicit status alert messages
                if "alerta" in data and data["alerta"]:
                    self.state_manager.add_alert(f"sensor_alert: {data['alerta']}")

            # 2. Topic: control/led
            elif suffix == "control/led":
                val = self._parse_boolean_payload(payload_str)
                self.state_manager.update_actuator_state("led", val)

            # 3. Topic: control/buzzer
            elif suffix == "control/buzzer":
                val = self._parse_boolean_payload(payload_str)
                self.state_manager.update_actuator_state("buzzer", val)

            # 4. Topic: movimiento
            elif suffix == "movimiento":
                val = self._parse_boolean_payload(payload_str)
                self.state_manager.update_actuator_state("movimiento", val)

            # 5. Topic: acceso/estado
            elif suffix == "acceso/estado":
                data = json.loads(payload_str)
                estado = data.get("estado", "").lower()
                # If access is allowed, a person is verified/present inside the door area
                if estado == "permitido":
                    self.state_manager.update_actuator_state("persona", True)
                elif estado in ("denegado", "desconocido"):
                    self.state_manager.update_actuator_state("persona", False)

            # 6. Topic: camara/evento
            elif suffix == "camara/evento":
                data = json.loads(payload_str)
                evento = data.get("evento", "").lower()
                if evento == "persona_detectada":
                    self.state_manager.update_actuator_state("persona", True)

            # 7. Topic: alerta (Custom alert updates)
            elif suffix == "alerta":
                try:
                    data = json.loads(payload_str)
                    if isinstance(data, dict) and "tipo" in data:
                        self.state_manager.add_alert(data["tipo"])
                except json.JSONDecodeError:
                    # Treat payload as raw alert message
                    if payload_str:
                        self.state_manager.add_alert(payload_str)

        except Exception as e:
            logger.error("Error processing MQTT message on topic %s: %s", topic, e, exc_info=True)

    def _parse_boolean_payload(self, payload_str: str) -> bool:
        """Helper to parse raw payload values into booleans (handles ON/OFF, true/false, JSON)."""
        if not payload_str:
            return False

        # Check raw text indicators
        if payload_str.upper() in ("ON", "SI", "TRUE", "1"):
            return True
        if payload_str.upper() in ("OFF", "NO", "FALSE", "0"):
            return False

        # Attempt to parse as JSON
        try:
            data = json.loads(payload_str)
            if isinstance(data, dict):
                # Check typical boolean parameters used in the project
                return (
                    data.get("estado") is True
                    or data.get("valor") is True
                    or data.get("accion") == "ON"
                )
            return bool(data)
        except json.JSONDecodeError:
            return False
