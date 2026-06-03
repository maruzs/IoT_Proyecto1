import asyncio
import logging
import os

import uvicorn
from fastapi import FastAPI

from .api import routes
from .database.db import init_db
from .face_processor.processor import FaceProcessor
from .io_layer.mode_resolver import resolve_mode
from .mqtt_client.client import MQTTClient

logger = logging.getLogger(__name__)

app = FastAPI(title="IoT Access Control")

mode = os.environ.get("MODE", "DEV_LOCAL")


@app.on_event("startup")
async def startup():
    # 1. Initialize database
    init_db()

    # 2. Resolve I/O mode (PROD_MQTT needs MQTTClient first)
    mqtt_client = None
    if mode == "PROD_MQTT":
        mqtt_client = MQTTClient()
        video_source, command_output = resolve_mode(
            publish_func=mqtt_client.publish,
        )
        mqtt_client.set_url_callback(video_source.set_url)
        mqtt_client.connect()
    else:
        video_source, command_output = resolve_mode()

    # 3. Create FaceProcessor
    processor = FaceProcessor()

    # 4. Inject state into FastAPI app
    app.state.io = (video_source, command_output)
    app.state.processor = processor
    app.state.mqtt = mqtt_client
    app.state.mode = mode

    # 5. Start background burst-processing loop
    asyncio.create_task(_processing_loop())


@app.on_event("shutdown")
async def shutdown():
    mqtt_client = getattr(app.state, "mqtt", None)
    io = getattr(app.state, "io", None)
    video_source = io[0] if io else None

    if mqtt_client:
        mqtt_client.disconnect()
    if video_source:
        video_source.release()


# Register API routes
app.include_router(routes.router)


async def _processing_loop():
    """Background loop: read frames, collect 5-second bursts, process faces."""
    io = app.state.io
    processor = app.state.processor
    video_source, command_output = io

    frames_buffer = []
    burst_start = None
    BURST_DURATION = 5.0

    while True:
        frame = await asyncio.to_thread(video_source.read_frame)
        if frame is not None:
            frames_buffer.append(frame)
            if burst_start is None:
                burst_start = asyncio.get_event_loop().time()

            elapsed = asyncio.get_event_loop().time() - burst_start
            if elapsed >= BURST_DURATION:
                try:
                    result = await asyncio.to_thread(processor.process_burst, frames_buffer)
                    if result["estado"] == "permitido":
                        await asyncio.to_thread(
                            command_output.notify_access,
                            result["usuario"],
                            result.get("usuario_id"),
                        )
                        await asyncio.to_thread(command_output.door_open, 3)
                    else:
                        await asyncio.to_thread(
                            command_output.notify_unknown, result.get("frame")
                        )
                except Exception:
                    logger.exception("Burst processing failed")
                frames_buffer = []
                burst_start = None

        await asyncio.sleep(0.033)  # ~30 FPS cap


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
