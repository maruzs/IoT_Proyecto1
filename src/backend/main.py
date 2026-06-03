import os
from fastapi import FastAPI
from .database import db
from .io_layer.mode_resolver import resolve_mode
from .face_processor.processor import FaceProcessor
from .api.routes import router

app = FastAPI()
app.include_router(router)


@app.on_event("startup")
async def startup():
    db.init_db()
    mode = os.environ.get("MODE", "DEV_LOCAL")
    if mode == "DEV_LOCAL":
        app.state.io = resolve_mode()
    else:
        # PROD_MQTT: placeholder until PR 3c injects the MQTT publisher.
        app.state.io = (None, None)
    app.state.processor = FaceProcessor()
