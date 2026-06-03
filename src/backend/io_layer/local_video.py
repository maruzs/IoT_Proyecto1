import cv2
import numpy as np
from .video_source import VideoSource


class LocalVideoSource(VideoSource):
    """Video source backed by the local webcam (cv2.VideoCapture(0))."""

    def __init__(self) -> None:
        self._cap = cv2.VideoCapture(0)
        if not self._cap.isOpened():
            raise RuntimeError("Failed to open local webcam (index 0)")

    def read_frame(self) -> np.ndarray | None:
        ret, frame = self._cap.read()
        return frame if ret else None

    def release(self) -> None:
        self._cap.release()
