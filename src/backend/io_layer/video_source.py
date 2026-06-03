from abc import ABC, abstractmethod
import numpy as np


class VideoSource(ABC):
    """Abstract base for video input sources."""

    @abstractmethod
    def read_frame(self) -> np.ndarray | None:
        """Return the next frame as a BGR numpy array, or None if unavailable."""
        ...

    @abstractmethod
    def release(self) -> None:
        """Release any underlying resources."""
        ...
