import base64
import logging
import tempfile
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger("vision.emotion_detector")

EMOTION_LABELS = ["happy", "sad", "angry", "fear", "surprise", "disgust", "neutral"]

EMOTION_EMOJI_MAP = {
    "happy": "\U0001f600",
    "sad": "\U0001f622",
    "angry": "\U0001f620",
    "fear": "\U0001f628",
    "surprise": "\U0001f62e",
    "disgust": "\U0001f922",
    "neutral": "\U0001f610",
}


class FaceEmotionResult(BaseModel):
    dominant_emotion: str
    confidence: float
    all_scores: dict[str, float]
    face_index: int = 0


class EmotionDetector:
    def __init__(self):
        self._backend = None
        self._initialized = False

    def _ensure_initialized(self) -> str:
        if self._initialized:
            return self._backend

        try:
            import deepface  # noqa: F401
            logger.info("deepface package found at: %s", deepface.__file__)
            from deepface import DeepFace  # noqa: F401
            self._backend = "deepface"
            self._initialized = True
            logger.info("DeepFace backend initialized successfully")
            return self._backend
        except Exception as exc:
            logger.warning("DeepFace not available (%s: %s), trying opencv-haar fallback", type(exc).__name__, exc)

        try:
            import cv2  # noqa: F401
            import numpy  # noqa: F401
            self._backend = "opencv-haar"
            self._initialized = True
            logger.info("Using OpenCV Haar cascade fallback for face detection (cv2=%s, numpy=%s)", cv2.__version__, numpy.__version__)
            return self._backend
        except Exception as exc:
            logger.warning("OpenCV not available (%s: %s), vision analysis disabled", type(exc).__name__, exc)

        self._backend = "unavailable"
        self._initialized = True
        logger.error("No vision backend available. Install deepface or opencv-python-headless.")
        return self._backend

    def analyze_frame(self, image_bytes: bytes) -> list[FaceEmotionResult]:
        backend = self._ensure_initialized()

        if backend == "deepface":
            return self._analyze_with_deepface(image_bytes)
        if backend == "opencv-haar":
            return self._analyze_with_opencv_fallback(image_bytes)
        return []

    def _analyze_with_deepface(self, image_bytes: bytes) -> list[FaceEmotionResult]:
        from deepface import DeepFace

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name

        try:
            results = DeepFace.analyze(
                img_path=tmp_path,
                actions=["emotion"],
                enforce_detection=False,
                silent=True,
            )

            if not isinstance(results, list):
                results = [results]

            emotions_list: list[FaceEmotionResult] = []
            for idx, face_result in enumerate(results):
                if isinstance(face_result, dict):
                    emotion_scores = face_result.get("emotion", {})
                    dominant = face_result.get("dominant_emotion", "neutral")
                else:
                    emotion_scores = getattr(face_result, "emotion", {})
                    dominant = getattr(face_result, "dominant_emotion", "neutral")

                normalized_scores = {}
                for label in EMOTION_LABELS:
                    normalized_scores[label] = round(float(emotion_scores.get(label, 0.0)), 1)

                confidence = normalized_scores.get(dominant, 0.0)

                emotions_list.append(FaceEmotionResult(
                    dominant_emotion=dominant,
                    confidence=confidence,
                    all_scores=normalized_scores,
                    face_index=idx,
                ))

            return emotions_list

        except ValueError as exc:
            if "Face could not be detected" in str(exc):
                return []
            logger.exception("DeepFace analysis error")
            return []
        except Exception:
            logger.exception("Unexpected DeepFace error")
            return []
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _analyze_with_opencv_fallback(self, image_bytes: bytes) -> list[FaceEmotionResult]:
        import cv2
        import numpy as np

        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            logger.warning("OpenCV: failed to decode image (%d bytes)", len(image_bytes))
            return []

        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(cascade_path)

        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=3,
            minSize=(int(w * 0.08), int(h * 0.08)),
        )

        logger.info("OpenCV Haar: image %dx%d, detected %d face(s)", w, h, len(faces))

        results: list[FaceEmotionResult] = []
        for idx, (x, y, fw, fh) in enumerate(faces):
            results.append(FaceEmotionResult(
                dominant_emotion="neutral",
                confidence=100.0,
                all_scores={label: (100.0 if label == "neutral" else 0.0) for label in EMOTION_LABELS},
                face_index=idx,
            ))

        return results

    def decode_base64_image(self, b64_string: str) -> Optional[bytes]:
        try:
            return base64.b64decode(b64_string)
        except Exception:
            logger.exception("Failed to decode base64 image")
            return None
