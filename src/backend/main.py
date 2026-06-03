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

# Global lock to prevent overlapping captures
_capture_lock = asyncio.Lock()
_capturing = False


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

    # Register capture state
    app.state.capturing = False
    app.state.capture_lock = _capture_lock


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


async def run_capture(request, duration: float = 10.0):
    """Run a capture session: process frames in 3s sub-bursts,
    emitting results to DB as they happen so the frontend updates live."""
    io = request.app.state.io
    processor = request.app.state.processor
    video_source, command_output = io

    app.state.capturing = True
    SUB_BURST = 3.0  # process every 3 seconds
    frames_buffer = []
    last_result = {"estado": "sin_resultado"}
    deadline = asyncio.get_event_loop().time() + duration
    next_process = asyncio.get_event_loop().time() + SUB_BURST

    try:
        while asyncio.get_event_loop().time() < deadline:
            frame = await asyncio.to_thread(video_source.read_frame)
            if frame is not None:
                frames_buffer.append(frame)

            # Process sub-burst every SUB_BURST seconds
            if frames_buffer and asyncio.get_event_loop().time() >= next_process:
                result = await asyncio.to_thread(processor.process_burst, frames_buffer)
                if result["estado"] == "permitido":
                    await asyncio.to_thread(
                        command_output.notify_access,
                        result["usuario"],
                        result.get("usuario_id"),
                    )
                    await asyncio.to_thread(command_output.door_open, 3)
                elif result.get("frame") is not None:
                    await asyncio.to_thread(
                        command_output.notify_unknown, result.get("frame")
                    )
                last_result = {"estado": result["estado"], "usuario": result.get("usuario")}
                frames_buffer = []
                next_process = asyncio.get_event_loop().time() + SUB_BURST

            await asyncio.sleep(0.033)

        # Process remaining frames at the end
        if frames_buffer:
            result = await asyncio.to_thread(processor.process_burst, frames_buffer)
            if result["estado"] == "permitido":
                await asyncio.to_thread(
                    command_output.notify_access,
                    result["usuario"],
                    result.get("usuario_id"),
                )
                await asyncio.to_thread(command_output.door_open, 3)
            elif result.get("frame") is not None:
                await asyncio.to_thread(
                    command_output.notify_unknown, result.get("frame")
                )
            last_result = {"estado": result["estado"], "usuario": result.get("usuario")}

        return last_result

    except Exception:
        logger.exception("Capture session failed")
        return {"estado": "error", "mensaje": "Error interno durante la captura"}
    finally:
        app.state.capturing = False
        await asyncio.to_thread(video_source.release)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
