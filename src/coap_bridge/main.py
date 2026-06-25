import asyncio
import logging
import signal

import aiocoap
import aiocoap.resource as resource

from coap_bridge.coap_server import GasResource, HumidityResource, TemperatureResource
from coap_bridge.config import Settings
from coap_bridge.mqtt_client import MQTTPublisher

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


async def main() -> None:
    _setup_logging()

    settings = Settings()

    publisher = MQTTPublisher(
        broker=settings.MQTT_BROKER,
        port=settings.MQTT_PORT,
        user=settings.MQTT_USER,
        password=settings.MQTT_PASS,
        tls_enabled=settings.MQTT_TLS,
        ca_cert_path=settings.MQTT_CA_CERT,
        equipo_id=settings.EQUIPO_ID,
    )
    publisher.connect()

    root = resource.Site()
    root.add_resource(
        [".well-known", "core"],
        resource.WKCResource(root.get_resources_as_linkheader),
    )
    root.add_resource(["sensores", "temperatura"], TemperatureResource(publisher))
    root.add_resource(["sensores", "humedad"], HumidityResource(publisher))
    root.add_resource(["sensores", "gas"], GasResource(publisher))

    bind_address = ("0.0.0.0", settings.COAP_PORT)
    await aiocoap.Context.create_server_context(root, bind=bind_address)
    logger.info("CoAP server bound to %s:%s/udp", *bind_address)

    shutdown_event = asyncio.Event()

    def _request_shutdown() -> None:
        logger.info("Shutdown signal received")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _request_shutdown)

    try:
        await shutdown_event.wait()
    finally:
        logger.info("Stopping CoAP bridge")
        publisher.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
