import pickle
import logging
from datetime import datetime, timedelta

import cv2
import face_recognition
import numpy as np

from ..database.db import get_all_users, insert_user

logger = logging.getLogger(__name__)


class FaceProcessor:
    """Core vision module: face detection, matching, and enrollment."""

    def __init__(self):
        self._cached_unknown_frame: np.ndarray | None = None
        self._enrollment_deadline: datetime | None = None
        self._best_bbox_area: float = 0

    def process_burst(self, frames: list[np.ndarray]) -> dict:
        """Process a burst of frames (5s capture).

        Returns:
            {"estado": "permitido"|"denegado", "usuario": str|None, "frame": np.ndarray|None}
        """
        self._cached_unknown_frame = None
        self._enrollment_deadline = None
        self._best_bbox_area = 0

        for frame in frames:
            try:
                faces = self._detect_faces(frame)
            except Exception:
                logger.exception("Face detection failed on a frame; skipping")
                continue

            if not faces:
                continue

            self._select_best_frame(frame, faces)

            for _bbox, encoding in faces:
                match = self._match_face(encoding)
                if match:
                    return {
                        "estado": "permitido",
                        "usuario": match["nombre"],
                        "usuario_id": match["id"],
                        "frame": None,
                    }

        if self._cached_unknown_frame is not None:
            self._enrollment_deadline = datetime.now() + timedelta(seconds=60)
            return {
                "estado": "denegado",
                "usuario": None,
                "frame": self._cached_unknown_frame,
            }

        return {"estado": "denegado", "usuario": None, "frame": None}

    def enroll(self, nombre: str) -> int:
        """Enroll the cached unknown frame.

        Returns:
            The newly created user_id.

        Raises:
            ValueError: If no frame is cached or the 60s enrollment window expired.
        """
        if self._cached_unknown_frame is None:
            raise ValueError("No cached unknown frame to enroll")

        if self._enrollment_deadline is not None and datetime.now() > self._enrollment_deadline:
            self._cached_unknown_frame = None
            self._enrollment_deadline = None
            raise ValueError("Enrollment deadline expired")

        faces = self._detect_faces(self._cached_unknown_frame)
        if len(faces) != 1:
            raise ValueError(
                f"Cached frame must contain exactly one face, found {len(faces)}"
            )

        encoding = faces[0][1]
        encoding_blob = pickle.dumps(encoding)
        user_id = insert_user(nombre, encoding_blob)

        self._cached_unknown_frame = None
        self._enrollment_deadline = None
        self._best_bbox_area = 0
        return user_id

    def _detect_faces(self, frame: np.ndarray) -> list[tuple]:
        """Returns list of (bbox, encoding) for faces in frame."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb)
        encodings = face_recognition.face_encodings(rgb, locations)
        results = []
        for (top, right, bottom, left), enc in zip(locations, encodings):
            bbox = {"top": top, "right": right, "bottom": bottom, "left": left}
            results.append((bbox, enc))
        return results

    def _match_face(self, encoding: np.ndarray) -> dict | None:
        """Compare encoding against all enrolled authorized users.

        Returns:
            {"id": user_id, "nombre": name, "confidence": float} or None.
        """
        users = [u for u in get_all_users() if u["autorizado"]]
        if not users:
            return None

        known_encodings = [pickle.loads(u["rostro_encoding"]) for u in users]
        matches = face_recognition.compare_faces(
            known_encodings, encoding, tolerance=0.6
        )

        if True not in matches:
            return None

        distances = face_recognition.face_distance(known_encodings, encoding)
        best_idx = min(
            (i for i, m in enumerate(matches) if m), key=lambda i: distances[i]
        )

        return {
            "id": users[best_idx]["id"],
            "nombre": users[best_idx]["nombre"],
            "confidence": float(1 - distances[best_idx]),
        }

    def _select_best_frame(self, frame: np.ndarray, faces: list[tuple]) -> None:
        """Keep frame with largest face bbox area."""
        for bbox, _encoding in faces:
            area = (bbox["right"] - bbox["left"]) * (bbox["bottom"] - bbox["top"])
            if area > self._best_bbox_area:
                self._best_bbox_area = area
                self._cached_unknown_frame = frame.copy()
