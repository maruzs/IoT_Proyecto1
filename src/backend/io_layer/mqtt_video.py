import cv2
import numpy as np
import threading
import time
from .video_source import VideoSource


class MQTTVideoSource(VideoSource):
    """Video source that receives JPEG frames via MQTT (``set_frame``).
    """

    def __init__(self) -> None:
        self._latest_frame: np.ndarray | None = None
        self._frame_lock = threading.Lock()
        self._last_frame_time: float = 0.0
        self._frame_interval: float = 0.033  # ~30 fps target

    def set_frame(self, frame_bytes: bytes) -> None:
        """Decode incoming JPEG bytes and store the latest frame."""
        if not frame_bytes:
            return
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is not None:
            with self._frame_lock:
                self._latest_frame = frame

    def read_frame(self) -> np.ndarray | None:
        """Return the latest frame without consuming it.
        Multiple consumers can read the same frame.
        """
        with self._frame_lock:
            frame = self._latest_frame
        return frame

    def release(self) -> None:
        with self._frame_lock:
            self._latest_frame = None
