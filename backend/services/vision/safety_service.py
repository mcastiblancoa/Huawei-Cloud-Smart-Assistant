import logging
import time
from typing import Optional

from .safety_detector import SafetyDetector

logger = logging.getLogger("vision.safety_service")


class SafetyService:
    def __init__(self):
        self._detector = SafetyDetector()

    def analyze_image(self, image_bytes: bytes) -> dict:
        started_at = time.perf_counter()

        try:
            result = self._detector.analyze_frame(image_bytes)
        except Exception:
            logger.exception("Error analyzing safety image")
            return self._build_error_response("processing_error")

        elapsed_ms = round((time.perf_counter() - started_at) * 1000)
        result["latency_ms"] = elapsed_ms
        return result

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
            "total_persons": 0,
            "compliant_persons": 0,
            "compliance_rate": 0.0,
            "persons": [],
            "all_detections": [],
            "ppe_summary": {},
            "latency_ms": 0,
        }
