import logging
import time
from typing import Optional

from .emotion_detector import EmotionDetector, FaceEmotionResult

logger = logging.getLogger("vision.sentiment_service")


class SentimentService:
    def __init__(self):
        self._detector = EmotionDetector()

    def analyze_image(
        self,
        image_bytes: bytes,
    ) -> dict:
        started_at = time.perf_counter()

        try:
            faces = self._detector.analyze_frame(image_bytes)
        except Exception:
            logger.exception("Error analyzing image frame")
            return self._build_error_response("processing_error")

        elapsed_ms = round((time.perf_counter() - started_at) * 1000)

        if not faces:
            return {
                "status": "no_face",
                "dominant_emotion": None,
                "confidence": None,
                "all_scores": None,
                "faces": [],
                "face_count": 0,
                "latency_ms": elapsed_ms,
            }

        primary = faces[0]
        return {
            "status": "success",
            "dominant_emotion": primary.dominant_emotion,
            "confidence": primary.confidence,
            "all_scores": primary.all_scores,
            "faces": [f.model_dump() for f in faces],
            "face_count": len(faces),
            "latency_ms": elapsed_ms,
        }

    def analyze_base64(self, b64_image: str) -> dict:
        image_bytes = self._detector.decode_base64_image(b64_image)
        if image_bytes is None:
            return self._build_error_response("invalid_image")
        return self.analyze_image(image_bytes)

    @staticmethod
    def _build_error_response(error: str) -> dict:
        return {
            "status": "error",
            "error": error,
            "dominant_emotion": None,
            "confidence": None,
            "all_scores": None,
            "faces": [],
            "face_count": 0,
            "latency_ms": 0,
        }
