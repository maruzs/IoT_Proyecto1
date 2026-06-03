import json
import time
from typing import Callable
import numpy as np
from ..database.db import insert_event
from .command_output import CommandOutput


class MQTTCommandOutput(CommandOutput):
    """MQTT output adapter: publishes access decisions and door commands
    via an injected ``publish_func``.
    """

    def __init__(self, publish_func: Callable[[str, str], None]) -> None:
        self._publish = publish_func

    def door_open(self, duration: int = 3) -> None:
        self._publish("control/led_puerta", json.dumps({"accion": "ON"}))
        time.sleep(duration)
        self._publish("control/led_puerta", json.dumps({"accion": "OFF"}))

    def notify_unknown(self, frame: np.ndarray | None) -> None:
        if frame is not None:
            self._publish(
                "acceso/estado",
                json.dumps({"estado": "denegado", "usuario": "desconocido"}),
            )
            self._publish(
                "acceso/enrolar",
                json.dumps({"accion": "enrolar", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}),
            )
            insert_event("Desconocido Detectado")
        else:
            insert_event("Sin Rostro")

    def notify_access(self, user_name: str, user_id: int | None = None) -> None:
        self._publish(
            "acceso/estado",
            json.dumps({"estado": "permitido", "usuario": user_name}),
        )
        insert_event("Entrada Automática", usuario_id=user_id)
