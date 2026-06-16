import logging
import sys

import uvicorn
from fastapi import FastAPI

from .api import routes
from .config import Settings
from .mqtt_client import MQTTPublisher
from .ollama_client import OllamaClient

logger = logging.getLogger(__name__)

app = FastAPI(title="LLM Gateway", version="1.0.0")


def _configure_logging() -> None:
    """Configure structured logging to stdout."""
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(fmt)
    for name in ("src.llm_gateway", "llm_gateway"):
        lg = logging.getLogger(name)
        lg.setLevel(logging.INFO)
        if not any(isinstance(h, logging.StreamHandler) for h in lg.handlers):
            lg.addHandler(handler)
        lg.propagate = False
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


@app.on_event("startup")
async def startup():
    _configure_logging()
    settings = Settings()

    logger.info(
        "Starting LLM Gateway | model=%s | broker=%s:%s | equipo=%s",
        settings.OLLAMA_MODEL,
        settings.MQTT_BROKER,
        settings.MQTT_PORT,
        settings.EQUIPO_ID,
    )

    ollama = OllamaClient(
        base_url=settings.OLLAMA_URL,
        model=settings.OLLAMA_MODEL,
        timeout=settings.OLLAMA_TIMEOUT,
        max_retries=settings.MAX_RETRIES,
    )
    app.state.ollama = ollama

    mqtt = MQTTPublisher(
        broker=settings.MQTT_BROKER,
        port=settings.MQTT_PORT,
        user=settings.MQTT_USER,
        password=settings.MQTT_PASS,
        tls_enabled=settings.MQTT_TLS,
        ca_cert_path=settings.MQTT_CA_CERT,
        equipo_id=settings.EQUIPO_ID,
    )
    mqtt.connect()
    app.state.mqtt = mqtt


@app.on_event("shutdown")
async def shutdown():
    ollama = getattr(app.state, "ollama", None)
    mqtt = getattr(app.state, "mqtt", None)

    if ollama is not None:
        try:
            await ollama.close()
            logger.info("Ollama client closed")
        except Exception:
            logger.exception("Error closing Ollama client")

    if mqtt is not None:
        try:
            mqtt.disconnect()
            logger.info("MQTT publisher disconnected")
        except Exception:
            logger.exception("Error disconnecting MQTT publisher")


app.include_router(routes.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
