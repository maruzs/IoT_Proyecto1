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

    def __init__(self, publish_func: Callable[[str, str], None], topic_base: str) -> None:
        self._publish = publish_func
        self._topic_base = topic_base.rstrip("/") + "/"

    def _topic(self, suffix: str) -> str:
        return f"{self._topic_base}{suffix}"

    def door_open(self, duration: int = 3) -> None:
        self._publish(self._topic("control/led_puerta"), json.dumps({"accion": "ON"}))
        time.sleep(duration)
        self._publish(self._topic("control/led_puerta"), json.dumps({"accion": "OFF"}))

    def notify_unknown(self, frame: np.ndarray) -> None:
        self._publish(
            self._topic("acceso/estado"),
            json.dumps({"estado": "denegado", "usuario": "desconocido"}),
        )
        self._publish(
            self._topic("acceso/enrolar"),
            json.dumps({"accion": "enrolar", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}),
        )
        insert_event("Desconocido Detectado")

    def notify_access(self, user_name: str) -> None:
        self._publish(
            self._topic("acceso/estado"),
            json.dumps({"estado": "permitido", "usuario": user_name}),
        )
        insert_event("Entrada Automática")
