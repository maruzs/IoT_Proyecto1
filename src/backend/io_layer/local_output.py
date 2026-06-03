import cv2
import numpy as np
from ..database.db import insert_event
from .command_output import CommandOutput

_cached_unknown_frame: np.ndarray | None = None


class LocalCommandOutput(CommandOutput):
    """Local output: console prints, cv2.imshow, and SQLite events."""

    def door_open(self, duration: int = 3) -> None:
        print(f"PUERTA ABIERTA por {duration}s")

    def notify_unknown(self, frame: np.ndarray | None) -> None:
        global _cached_unknown_frame
        if frame is not None:
            _cached_unknown_frame = frame.copy()
            print("DESCONOCIDO DETECTADO")
            insert_event("Desconocido Detectado")
        else:
            print("SIN ROSTRO — no se detecto ninguna cara")
            insert_event("Sin Rostro")

    def notify_access(self, user_name: str, user_id: int | None = None) -> None:
        print(f"ACCESO PERMITIDO: {user_name}")
        insert_event("Entrada Automática", usuario_id=user_id)

    def show_frame(self, frame: np.ndarray) -> None:
        cv2.imshow("IoT Access Control", frame)
        cv2.waitKey(1)
