import cv2
import numpy as np
import time
from .video_source import VideoSource


class MQTTVideoSource(VideoSource):
    """Video source that pulls frames from an HTTP MJPEG stream URL
    received via MQTT (``set_url``).
    """

    def __init__(self) -> None:
        self._url: str | None = None
        self._cap: cv2.VideoCapture | None = None
        self._last_frame_time: float = 0.0
        self._frame_interval: float = 0.033  # ~30 fps target
        self._url_set_time: float = 0.0
        self._url_timeout: float = 10.0

    def set_url(self, url: str) -> None:
        """Update the stream URL and reset the capture."""
        self._url = url
        self._url_set_time = time.time()
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def read_frame(self) -> np.ndarray | None:
        if self._url is None:
            return None

        now = time.time()

        # URL timeout: if 10s have passed since the URL was set, declare dead.
        if now - self._url_set_time > self._url_timeout:
            if self._cap is not None:
                self._cap.release()
                self._cap = None
            return None

        # Lazily open capture on first valid call after URL is set.
        if self._cap is None:
            self._cap = cv2.VideoCapture(self._url)
            if not self._cap.isOpened():
                self._cap = None
                return None

        # Framerate limiting: skip (grab without decode) until interval elapsed.
        if now - self._last_frame_time < self._frame_interval:
            if not self._cap.grab():
                self._cap.release()
                self._cap = None
                return None
            return None

        ret, frame = self._cap.read()
        if not ret:
            self._cap.release()
            self._cap = None
            return None

        self._last_frame_time = now
        return frame

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._url = None
