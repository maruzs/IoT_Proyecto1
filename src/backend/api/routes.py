import os
import asyncio

import cv2
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from ..database.db import get_last_event, get_history, insert_event, _to_chile_time
from ..face_processor.processor import FaceProcessor

router = APIRouter(prefix="/api")


class EnrollRequest(BaseModel):
    nombre: str


@router.get("/ultimo-evento")
async def ultimo_evento(request: Request) -> JSONResponse:
    """Get last access event from historial."""
    event = get_last_event()
    result = event or {}
    # Attach enrollment deadline if active
    processor: FaceProcessor = request.app.state.processor
    deadline = processor.get_enrollment_deadline()
    if deadline is not None:
        result["enrollment_deadline"] = deadline.isoformat()
        result["enrollable"] = True
    else:
        result["enrollable"] = False
    return JSONResponse(content=result)


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


def _placeholder_frame():
    """Return a 'Sin señal' placeholder frame."""
    import numpy as np
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:] = (30, 30, 30)  # dark grey
    cv2.putText(frame, "Sin senal de camara", (100, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 2)
    cv2.putText(frame, "Esperando ESP32-CAM...", (120, 280),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 150, 150), 1)
    return frame


async def _mjpeg_generator(video_source, get_capturing):
    """Yield MJPEG chunks. Only reads camera while capturing."""
    while True:
        if get_capturing():
            frame = video_source.read_frame()
            if frame is None:
                frame = _placeholder_frame()
        else:
            frame = _placeholder_frame()
            await asyncio.sleep(0.5)  # slow refresh when idle

        ret, jpeg = cv2.imencode(".jpg", frame)
        if ret:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + jpeg.tobytes()
                + b"\r\n"
            )
        if not get_capturing():
            await asyncio.sleep(0.5)
        else:
            await asyncio.sleep(0.05)


@router.get("/stream")
async def stream(request: Request):
    """MJPEG stream relay.

    Only reads camera during active capture sessions.
    Otherwise serves placeholder.
    """
    video_source = request.app.state.io[0]

    def get_capturing():
        return getattr(request.app.state, "capturing", False)

    return StreamingResponse(
        _mjpeg_generator(video_source, get_capturing),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.post("/capturar")
async def capturar(request: Request) -> JSONResponse:
    """Trigger a 10-second capture session. Processes the burst and
    returns the result. Blocks until capture completes."""
    from ..main import run_capture  # deferred import to avoid circular dependency

    if request.app.state.capturing:
        return JSONResponse(
            content={"estado": "ocupado", "mensaje": "Captura en progreso"},
            status_code=409,
        )

    async with request.app.state.capture_lock:
        result = await run_capture(request, duration=10.0)

    return JSONResponse(content=result)
