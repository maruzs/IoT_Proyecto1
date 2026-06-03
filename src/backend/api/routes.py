import os
import asyncio

import cv2
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from ..database.db import get_last_event, get_history, insert_event
from ..face_processor.processor import FaceProcessor

router = APIRouter(prefix="/api")


class EnrollRequest(BaseModel):
    nombre: str


@router.get("/ultimo-evento")
async def ultimo_evento(request: Request) -> JSONResponse:
    """Get last access event from historial."""
    event = get_last_event()
    return JSONResponse(content=event or {})


@router.get("/historial")
async def historial(limit: int = 50) -> JSONResponse:
    """Get last N events."""
    events = get_history(limit)
    return JSONResponse(content=events)


@router.post("/enrolar")
async def enrolar(request: Request, data: EnrollRequest) -> JSONResponse:
    """Enroll an unknown face. Body: {"nombre": "..."}. Returns 200/400/404."""
    processor: FaceProcessor = request.app.state.processor
    try:
        user_id = processor.enroll(data.nombre)
    except ValueError as exc:
        msg = str(exc)
        if "expired" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    return JSONResponse(content={"id": user_id, "nombre": data.nombre})


@router.post("/abrir-puerta")
async def abrir_puerta(request: Request) -> JSONResponse:
    """Manual door open. Calls io[1].door_open(3)."""
    io = request.app.state.io
    io[1].door_open(3)
    insert_event("Apertura Manual")
    return JSONResponse(content={"status": "ok"})


async def _mjpeg_generator(video_source):
    """Yield MJPEG chunks from a VideoSource."""
    while True:
        frame = video_source.read_frame()
        if frame is not None:
            ret, jpeg = cv2.imencode(".jpg", frame)
            if ret:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + jpeg.tobytes()
                    + b"\r\n"
                )
        await asyncio.sleep(0.05)


@router.get("/stream")
async def stream(request: Request):
    """MJPEG stream relay.

    In DEV_LOCAL: reads from LocalVideoSource, returns MJPEG StreamingResponse.
    In PROD_MQTT: placeholder until streaming is wired in a later PR.
    """
    mode = os.environ.get("MODE", "DEV_LOCAL")
    if mode == "DEV_LOCAL":
        video_source = request.app.state.io[0]
        return StreamingResponse(
            _mjpeg_generator(video_source),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )
    return JSONResponse({"status": "stream via proxy, use MJPEG endpoint"})
