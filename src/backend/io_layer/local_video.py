import cv2
import time
import numpy as np
from .video_source import VideoSource


class LocalVideoSource(VideoSource):
    """Video source backed by the local webcam (cv2.VideoCapture(0)).

    The camera is opened on-demand and automatically released after
    a short idle period to keep the webcam turned off when not in use.
    """

    def __init__(self) -> None:
        self._cap: cv2.VideoCapture | None = None
        self._last_read: float = 0
        self._IDLE_TIMEOUT = 2.0  # release camera after 2s of inactivity

    def _ensure_open(self) -> bool:
        """Open the camera if not already open. Returns True on success."""
        if self._cap is not None and self._cap.isOpened():
            return True
        try:
            self._cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        except Exception:
            self._cap = None
            return False
        if not self._cap.isOpened():
            self._cap.release()
            self._cap = None
            return False
        return True

    def read_frame(self) -> np.ndarray | None:
        if not self._ensure_open():
            return None
        ret, frame = self._cap.read()
        self._last_read = time.monotonic()
        if not ret:
            self._maybe_release()
            return None
        return frame

    def _maybe_release(self) -> None:
        """Release camera if idle for too long."""
        if self._cap is not None and time.monotonic() - self._last_read > self._IDLE_TIMEOUT:
            self._cap.release()
            self._cap = None

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
