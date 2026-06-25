import json
import logging
import ssl

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTPublisher:
    """MQTT publisher using paho-mqtt with TLS support and reconnect logic.

    Adapted from the llm_gateway MQTT client. The topic layout is fixed to
    ``smarthome/{equipo_id}/sensores/{suffix}`` so each sensor type is
    published to its own MQTT topic.
    """

    def __init__(
        self,
        broker: str,
        port: int,
        user: str,
        password: str,
        tls_enabled: bool,
        ca_cert_path: str,
        equipo_id: str,
    ) -> None:
        self.broker = broker
        self.port = port
        self.user = user
        self.password = password
        self.tls_enabled = tls_enabled
        self.ca_cert_path = ca_cert_path
        self.equipo_id = equipo_id

        # paho-mqtt v1 / v2 compatibility — same pattern as llm_gateway
        try:
            self.client = mqtt.Client(
                client_id=f"coap-bridge-{self.equipo_id}",
            )
        except TypeError:
            self.client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION1,
                client_id=f"coap-bridge-{self.equipo_id}",
            )

        # Built-in exponential backoff reconnect: 1s -> 2s -> 4s -> ... 30s
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

    def connect(self) -> None:
        """Connect to broker with optional TLS and auth, then start network loop."""
        if self.tls_enabled:
            context = ssl.create_default_context()
            context.load_verify_locations(self.ca_cert_path)
            self.client.tls_set_context(context)

        self.client.username_pw_set(self.user, self.password)
        self.client.on_connect = self._on_connect
        self.client.on_publish = self._on_publish
        self.client.on_disconnect = self._on_disconnect
        self.client.connect(self.broker, self.port)
        self.client.loop_start()

    def publish(self, topic_suffix: str, payload: dict) -> bool:
        """Publish a JSON payload to ``smarthome/{equipo_id}/sensores/{suffix}`` with QoS 1.

        Returns True on best-effort publish (actual confirmation via on_publish).
        """
        full_topic = f"smarthome/{self.equipo_id}/sensores/{topic_suffix}"
        message = json.dumps(payload)
        result = self.client.publish(full_topic, message, qos=1)
        return result.rc == 0

    def disconnect(self) -> None:
        """Stop the network loop and disconnect cleanly."""
        self.client.loop_stop()
        self.client.disconnect()

    def is_connected(self) -> bool:
        """Return whether the client is currently connected to the broker."""
        return self.client.is_connected()

    # ------------------------------------------------------------------ #
    # Internal callbacks
    # ------------------------------------------------------------------ #

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("MQTT connected to %s:%s", self.broker, self.port)
        else:
            logger.error("MQTT connection failed, rc=%s", rc)

    def _on_publish(self, client, userdata, mid):
        logger.debug("MQTT message published (mid=%s)", mid)

    def _on_disconnect(self, client, userdata, rc):
        if rc == 0:
            logger.info("MQTT disconnected cleanly")
        else:
            logger.warning("MQTT disconnected unexpectedly (rc=%s)", rc)
