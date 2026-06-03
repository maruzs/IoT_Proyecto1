import json
import logging
import os

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTClient:
    """paho-mqtt client with reconnect logic.

    This is the ONLY place in the codebase that creates an MQTT connection.
    """

    def __init__(
        self,
        broker_host: str = "mosquitto",
        broker_port: int = 1883,
        equipo_id: str = "equipoXX",
    ) -> None:
        self.broker_host = os.environ.get("MQTT_BROKER", broker_host)
        self.broker_port = broker_port
        self.equipo_id = os.environ.get("EQUIPO_ID", equipo_id)
        self.topic_base = f"smarthome/{self.equipo_id}"
        self._url_callback = None

        # paho-mqtt v1 / v2 compatibility
        try:
            self.client = mqtt.Client(client_id=f"backend-{self.equipo_id}")
        except TypeError:
            self.client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION1,
                client_id=f"backend-{self.equipo_id}",
            )

        # Built-in exponential backoff reconnect: 1s -> 2s -> 4s -> ... 30s
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

    def connect(self) -> None:
        """Connect to broker, set callbacks, and start the background network loop."""
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.client.connect(self.broker_host, self.broker_port)
        self.client.loop_start()

    def set_url_callback(self, callback) -> None:
        """Register callback invoked when ``camara/url`` arrives."""
        self._url_callback = callback

    def publish(self, topic_suffix: str, payload: str | dict) -> None:
        """Publish to ``{topic_base}/{topic_suffix}`` with QoS 1.

        Accepts either a pre-encoded JSON string or a dict (auto-encoded).
        """
        full_topic = f"{self.topic_base}/{topic_suffix}"
        if isinstance(payload, dict):
            payload = json.dumps(payload)
        self.client.publish(full_topic, payload, qos=1)

    def disconnect(self) -> None:
        """Stop network loop and disconnect cleanly."""
        self.client.loop_stop()
        self.client.disconnect()

    # ------------------------------------------------------------------ #
    # Internal callbacks
    # ------------------------------------------------------------------ #

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("MQTT connected to %s:%s", self.broker_host, self.broker_port)
            topic = f"{self.topic_base}/camara/url"
            client.subscribe(topic, qos=1)
            logger.info("Subscribed to %s", topic)
        else:
            logger.error("MQTT connection failed, rc=%s", rc)

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode("utf-8")
        logger.debug("MQTT message on %s: %s", topic, payload)

        if topic == f"{self.topic_base}/camara/url":
            try:
                data = json.loads(payload)
                url = data.get("url")
                if url and self._url_callback:
                    self._url_callback(url)
                    logger.info("Camera URL updated: %s", url)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON on %s: %s", topic, payload)

    def _on_disconnect(self, client, userdata, rc):
        if rc == 0:
            logger.info("MQTT disconnected cleanly")
        else:
            logger.warning("MQTT disconnected unexpectedly (rc=%s)", rc)
