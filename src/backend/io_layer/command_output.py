from abc import ABC, abstractmethod
import numpy as np


class CommandOutput(ABC):
    """Abstract base for access-control actuators and notifications."""

    @abstractmethod
    def door_open(self, duration: int = 3) -> None:
        """Trigger the door open actuator for the given duration in seconds."""
        ...

    @abstractmethod
    def notify_unknown(self, frame: np.ndarray) -> None:
        """Notify that an unknown face was detected, caching the frame."""
        ...

    @abstractmethod
    def notify_access(self, user_name: str, user_id: int | None = None) -> None:
        """Notify that an authorized user was granted access."""
        ...
