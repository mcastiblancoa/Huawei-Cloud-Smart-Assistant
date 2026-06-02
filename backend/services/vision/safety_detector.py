import base64
import logging
import tempfile
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger("vision.safety_detector")

PPE_CLASSES = {
    "hardhat": {"label_es": "Casco", "label_en": "Hardhat", "icon": "⛑️"},
    "helmet": {"label_es": "Casco", "label_en": "Helmet", "icon": "⛑️"},
    "safety_vest": {"label_es": "Chaleco", "label_en": "Safety Vest", "icon": "🦺"},
    "vest": {"label_es": "Chaleco", "label_en": "Vest", "icon": "🦺"},
    "goggles": {"label_es": "Gafas", "label_en": "Goggles", "icon": "🥽"},
    "glasses": {"label_es": "Gafas", "label_en": "Glasses", "icon": "🥽"},
    "face_shield": {"label_es": "Protector facial", "label_en": "Face Shield", "icon": "🛡️"},
    "mask": {"label_es": "Mascarilla", "label_en": "Mask", "icon": "😷"},
    "gloves": {"label_es": "Guantes", "label_en": "Gloves", "icon": "🧤"},
    "safety_boots": {"label_es": "Botas", "label_en": "Safety Boots", "icon": "🥾"},
    "boots": {"label_es": "Botas", "label_en": "Boots", "icon": "🥾"},
}

PERSON_CLASSES = {"person", "worker", "people"}

REQUIRED_PPE = ["hardhat", "safety_vest"]


class PPEItem(BaseModel):
    class_name: str
    confidence: float
    bbox: list[float]


class PersonDetection(BaseModel):
    person_index: int
    bbox: list[float]
    ppe: list[PPEItem]
    ppe_classes: list[str]
    missing_ppe: list[str]
    compliant: bool


class SafetyDetector:
    def __init__(self):
        self._model = None
        self._initialized = False
        self._model_source = None

    def _ensure_initialized(self):
        if self._initialized:
            return self._model is not None

        try:
            from ultralytics import YOLO
            logger.info("Ultralytics YOLO found, loading PPE model...")
            self._model = YOLO("yolov8n.pt")
            self._model_source = "yolov8n-coco"
            self._initialized = True
            logger.info("YOLOv8n (COCO) model loaded — will detect person + PPE via COCO classes")
            return True
        except Exception as exc:
            logger.warning("Ultralytics not available (%s: %s)", type(exc).__name__, exc)

        self._initialized = True
        self._model = None
        logger.error("No YOLO model available. Install ultralytics: pip install ultralytics")
        return False

    def analyze_frame(self, image_bytes: bytes) -> dict:
        if not self._ensure_initialized():
            return self._build_error("model_unavailable")

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name

        try:
            return self._analyze_with_yolo(tmp_path)
        except Exception:
            logger.exception("Error analyzing safety frame")
            return self._build_error("processing_error")
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _analyze_with_yolo(self, image_path: str) -> dict:
        results = self._model(image_path, conf=0.35, verbose=False)
        result = results[0]

        all_detections = []
        persons_raw = []

        if result.boxes is not None and len(result.boxes) > 0:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                xyxy = box.xyxy[0].tolist()
                class_name = result.names.get(cls_id, f"class_{cls_id}")

                all_detections.append({
                    "class_name": class_name,
                    "confidence": round(conf * 100, 1),
                    "bbox": [round(v, 1) for v in xyxy],
                })

                if class_name.lower() in PERSON_CLASSES or class_name.lower() == "person":
                    persons_raw.append({
                        "bbox": [round(v, 1) for v in xyxy],
                        "confidence": round(conf * 100, 1),
                    })

        persons: list[PersonDetection] = []
        for idx, person in enumerate(persons_raw):
            ppe_items = []
            ppe_classes = []
            px1, py1, px2, py2 = person["bbox"]

            for det in all_detections:
                if det["class_name"].lower() in PERSON_CLASSES:
                    continue
                dx1, dy1, dx2, dy2 = det["bbox"]
                cx = (dx1 + dx2) / 2
                cy = (dy1 + dy2) / 2
                if px1 <= cx <= px2 and py1 <= cy <= py2:
                    ppe_items.append(PPEItem(
                        class_name=det["class_name"],
                        confidence=det["confidence"],
                        bbox=det["bbox"],
                    ))
                    ppe_classes.append(det["class_name"].lower())

            missing = []
            for req in REQUIRED_PPE:
                found = any(req in cls or cls in req for cls in ppe_classes)
                if not found:
                    ppe_config = PPE_CLASSES.get(req, {})
                    missing.append(ppe_config.get("label_en", req))

            persons.append(PersonDetection(
                person_index=idx,
                bbox=person["bbox"],
                ppe=ppe_items,
                ppe_classes=ppe_classes,
                missing_ppe=missing,
                compliant=len(missing) == 0,
            ))

        total_persons = len(persons)
        compliant_persons = sum(1 for p in persons if p.compliant)
        compliance_rate = round((compliant_persons / total_persons) * 100, 1) if total_persons > 0 else 0.0

        ppe_summary = {}
        for det in all_detections:
            name = det["class_name"].lower()
            if name in PERSON_CLASSES or name == "person":
                continue
            if name not in ppe_summary:
                ppe_summary[name] = 0
            ppe_summary[name] += 1

        return {
            "status": "success",
            "total_persons": total_persons,
            "compliant_persons": compliant_persons,
            "compliance_rate": compliance_rate,
            "persons": [p.model_dump() for p in persons],
            "all_detections": all_detections,
            "ppe_summary": ppe_summary,
        }

    def decode_base64_image(self, b64_string: str) -> Optional[bytes]:
        try:
            return base64.b64decode(b64_string)
        except Exception:
            logger.exception("Failed to decode base64 image")
            return None

    @staticmethod
    def _build_error(error: str) -> dict:
        return {
            "status": "error",
            "error": error,
            "total_persons": 0,
            "compliant_persons": 0,
            "compliance_rate": 0.0,
            "persons": [],
            "all_detections": [],
            "ppe_summary": {},
        }
