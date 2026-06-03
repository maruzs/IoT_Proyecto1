import cv2
import numpy as np
from ..database.db import insert_event
from .command_output import CommandOutput

_cached_unknown_frame: np.ndarray | None = None


class LocalCommandOutput(CommandOutput):
    """Local output: console prints, cv2.imshow, and SQLite events."""

    def door_open(self, duration: int = 3) -> None:
        print(f"PUERTA ABIERTA por {duration}s")

    def notify_unknown(self, frame: np.ndarray) -> None:
        global _cached_unknown_frame
        _cached_unknown_frame = frame.copy()
        print("DESCONOCIDO DETECTADO")
        insert_event("Desconocido Detectado")

    def notify_access(self, user_name: str) -> None:
        print(f"ACCESO PERMITIDO: {user_name}")
        insert_event("Entrada Automática")

    def show_frame(self, frame: np.ndarray) -> None:
        cv2.imshow("IoT Access Control", frame)
        cv2.waitKey(1)
