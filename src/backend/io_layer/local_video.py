import cv2
import time
import numpy as np
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from .video_source import VideoSource


class LocalVideoSource(VideoSource):
    """Video source backed by the local webcam (cv2.VideoCapture(0)).

    The camera is opened on-demand with a timeout and automatically
    released after a short idle period.
    """

    _OPEN_TIMEOUT = 5.0   # max seconds to wait for camera open
    _IDLE_TIMEOUT = 2.0   # release camera after 2s of inactivity

    def __init__(self) -> None:
        self._cap: cv2.VideoCapture | None = None
        self._last_read: float = 0
        self._executor = ThreadPoolExecutor(max_workers=1)

    def _open_camera(self) -> cv2.VideoCapture | None:
        """Open the camera in a background thread. Returns cap or None."""
        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        if cap.isOpened():
            return cap
        cap.release()
        return None

    def _ensure_open(self) -> bool:
        """Open the camera with a timeout. Returns True on success."""
        if self._cap is not None and self._cap.isOpened():
            return True

        future = self._executor.submit(self._open_camera)
        try:
            self._cap = future.result(timeout=self._OPEN_TIMEOUT)
        except FuturesTimeoutError:
            future.cancel()
            self._cap = None
            return False

        return self._cap is not None

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
        self._executor.shutdown(wait=False)
