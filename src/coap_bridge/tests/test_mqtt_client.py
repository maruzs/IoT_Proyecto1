import json
from unittest.mock import MagicMock, patch

from coap_bridge.mqtt_client import MQTTPublisher


def _make_publisher(mock_client: MagicMock) -> MQTTPublisher:
    return MQTTPublisher(
        broker="mosquitto",
        port=8883,
        user="coap-bridge-equipo69",
        password="secret",
        tls_enabled=False,
        ca_cert_path="/certs/ca.crt",
        equipo_id="equipo69",
    )


@patch("coap_bridge.mqtt_client.mqtt.Client")
def test_publish_builds_sensor_topic(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    publisher = _make_publisher(mock_client)
    publisher.connect()

    payload = {"temperatura": 29.5}
    publisher.publish("temperatura", payload)

    mock_client.publish.assert_called_once()
    topic, message = mock_client.publish.call_args[0]
    assert topic == "smarthome/equipo69/sensores/temperatura"
    assert json.loads(message) == payload
    assert mock_client.publish.call_args.kwargs.get("qos") == 1


@patch("coap_bridge.mqtt_client.mqtt.Client")
def test_publish_returns_true_on_success(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.publish.return_value.rc = 0

    publisher = _make_publisher(mock_client)
    publisher.connect()

    result = publisher.publish("humedad", {"humedad": 65.2})
    assert result is True
