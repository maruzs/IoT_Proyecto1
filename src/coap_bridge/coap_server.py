import json
import logging

import aiocoap.resource as resource
from aiocoap import Message
from aiocoap.numbers.codes import Code

from coap_bridge.mqtt_client import MQTTPublisher

logger = logging.getLogger(__name__)


def validate_json(payload: bytes, expected_field: str) -> dict:
    """Parse a CoAP payload as JSON and ensure it contains the expected field.

    Args:
        payload: Raw request payload (bytes).
        expected_field: Sensor field that must be present in the JSON object.

    Returns:
        The parsed JSON object as a dict.

    Raises:
        ValueError: If the payload is not valid JSON or the expected field is missing.
    """
    try:
        data = json.loads(payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("Payload is not valid JSON") from exc

    if not isinstance(data, dict):
        raise ValueError("Payload JSON must be an object")

    if expected_field not in data:
        raise ValueError(f"Missing required field: {expected_field}")

    return data


class SensorResource(resource.Resource):
    """Base CoAP resource that validates sensor payloads and forwards them to MQTT."""

    sensor_type: str = ""
    expected_field: str = ""

    def __init__(self, publisher: MQTTPublisher) -> None:
        super().__init__()
        self.publisher = publisher

    async def render_post(self, request):
        try:
            data = validate_json(request.payload, self.expected_field)
            if not self.publisher.publish(self.sensor_type, data):
                logger.error("MQTT publish failed for /sensores/%s", self.sensor_type)
                return Message(code=Code.INTERNAL_SERVER_ERROR)
            return Message(code=Code.CHANGED)
        except ValueError as exc:
            logger.warning(
                "Invalid payload on /sensores/%s: %s",
                self.sensor_type,
                exc,
            )
            return Message(code=Code.BAD_REQUEST)
        except Exception:
            logger.exception("Unexpected error handling /sensores/%s", self.sensor_type)
            return Message(code=Code.INTERNAL_SERVER_ERROR)


class TemperatureResource(SensorResource):
    """CoAP resource for temperature readings."""

    sensor_type = "temperatura"
    expected_field = "temperatura"


class HumidityResource(SensorResource):
    """CoAP resource for humidity readings."""

    sensor_type = "humedad"
    expected_field = "humedad"


class GasResource(SensorResource):
    """CoAP resource for gas readings."""

    sensor_type = "gas"
    expected_field = "gas"
