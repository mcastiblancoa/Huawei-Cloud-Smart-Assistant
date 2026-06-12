import base64
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger("vision.safety_detector")

PPE_CLASSES = {
    "hardhat": {"label_es": "Casco", "label_en": "Hardhat", "icon": "⛑️"},
    "helmet": {"label_es": "Casco", "label_en": "Helmet", "icon": "⛑️"},
    "head": {"label_es": "Cabeza (sin casco)", "label_en": "Head (no hardhat)", "icon": "🚫"},
    "safety_vest": {"label_es": "Chaleco", "label_en": "Safety Vest", "icon": "🦺"},
    "vest": {"label_es": "Chaleco", "label_en": "Vest", "icon": "🦺"},
    "no_vest": {"label_es": "Sin chaleco", "label_en": "No Safety Vest", "icon": "🚫"},
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

_PPE_CLASS_MAP = {
    "hardhat": "hardhat",
    "helmet": "hardhat",
    "hard hat": "hardhat",
    "safety helmet": "hardhat",
    "head": "head",
    "no hardhat": "head",
    "no-hard hat": "head",
    "no-hardhat": "head",
    "no helmet": "head",
    "safety_vest": "safety_vest",
    "safety vest": "safety_vest",
    "vest": "safety_vest",
    "reflective vest": "safety_vest",
    "no vest": "no_vest",
    "no-safety vest": "no_vest",
    "no_safety_vest": "no_vest",
    "goggles": "goggles",
    "glasses": "glasses",
    "face_shield": "face_shield",
    "face shield": "face_shield",
    "mask": "mask",
    "gloves": "gloves",
    "safety_boots": "safety_boots",
    "safety boots": "safety_boots",
    "boots": "boots",
}

_NEGATIVE_CLASSES = {
    "no hardhat", "no-hard hat", "no-hardhat", "no helmet",
    "no vest", "no-safety vest", "no_safety_vest",
    "head",
}


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


_ROBOFLOW_PPE_MODEL = "ppe-detection-yfmym/3"


class SafetyDetector:
    def __init__(self):
        self._model = None
        self._initialized = False
        self._model_source = None
        self._use_roboflow = False

    def _ensure_initialized(self):
        if self._initialized:
            return self._model is not None or self._use_roboflow

        ppe_model_path = Path(__file__).resolve().parent.parent / "ppe_yolov8s.pt"
        if ppe_model_path.exists():
            try:
                from ultralytics import YOLO
                logger.info("Loading PPE-specific model: %s", ppe_model_path)
                self._model = YOLO(str(ppe_model_path))
                self._model_source = "ppe-yolov8s"
                self._initialized = True
                logger.info("PPE model loaded successfully — dedicated hardhat/vest detection")
                return True
            except Exception as exc:
                logger.warning("Failed to load PPE model (%s: %s)", type(exc).__name__, exc)

        if self._try_roboflow():
            self._initialized = True
            return True

        try:
            from ultralytics import YOLO
            logger.info("Loading fallback COCO model: yolov8n.pt")
            self._model = YOLO("yolov8n.pt")
            self._model_source = "yolov8n-coco"
            self._initialized = True
            logger.warning("COCO model loaded — PPE detection will be limited. Run: python download_ppe_model.py")
            return True
        except Exception as exc:
            logger.warning("Ultralytics not available (%s: %s)", type(exc).__name__, exc)

        self._initialized = True
        self._model = None
        logger.error("No YOLO model available. Set ROBOFLOW_API_KEY or install ultralytics.")
        return False

    def _try_roboflow(self) -> bool:
        api_key = os.environ.get("ROBOFLOW_API_KEY", "")
        if not api_key:
            logger.info("ROBOFLOW_API_KEY not set, skipping Roboflow cloud inference")
            return False
        try:
            from inference_sdk import InferenceHTTPClient
            self._roboflow_client = InferenceHTTPClient(
                api_url="https://detect.roboflow.com",
                api_key=api_key,
            )
            self._roboflow_model_id = _ROBOFLOW_PPE_MODEL
            self._use_roboflow = True
            self._model_source = "roboflow-cloud"
            logger.info("Roboflow cloud inference configured (model: %s)", _ROBOFLOW_PPE_MODEL)
            return True
        except ImportError:
            logger.info("inference_sdk not installed, skipping Roboflow cloud inference. pip install inference-sdk")
            return False
        except Exception as exc:
            logger.warning("Roboflow setup failed: %s", exc)
            return False

    def _map_class(self, raw_name: str) -> str:
        lower = raw_name.lower().strip()
        if lower in _PPE_CLASS_MAP:
            return _PPE_CLASS_MAP[lower]
        for key, mapped in _PPE_CLASS_MAP.items():
            if key in lower or lower in key:
                return mapped
        return lower

    def _is_person(self, class_name: str) -> bool:
        return class_name.lower() in PERSON_CLASSES or class_name.lower() == "person"

    def _is_ppe_positive(self, mapped_class: str) -> bool:
        if mapped_class in _NEGATIVE_CLASSES:
            return False
        if mapped_class in PERSON_CLASSES:
            return False
        return mapped_class in PPE_CLASSES

    def analyze_frame(self, image_bytes: bytes) -> dict:
        if not self._ensure_initialized():
            return self._build_error("model_unavailable")

        if self._use_roboflow:
            return self._analyze_with_roboflow(image_bytes)

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
        results = self._model(image_path, conf=0.25, verbose=False)
        result = results[0]

        all_detections = []
        persons_raw = []
        violations_raw = []

        if result.boxes is not None and len(result.boxes) > 0:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                xyxy = box.xyxy[0].tolist()
                class_name = result.names.get(cls_id, f"class_{cls_id}")
                mapped = self._map_class(class_name)

                det = {
                    "class_name": class_name,
                    "mapped_class": mapped,
                    "confidence": round(conf * 100, 1),
                    "bbox": [round(v, 1) for v in xyxy],
                }
                all_detections.append(det)

                if self._is_person(class_name):
                    persons_raw.append(det)

                if mapped in _NEGATIVE_CLASSES:
                    violations_raw.append(det)

        return self._build_result(all_detections, persons_raw, violations_raw)

    def decode_base64_image(self, b64_string: str) -> Optional[bytes]:
        try:
            return base64.b64decode(b64_string)
        except Exception:
            logger.exception("Failed to decode base64 image")
            return None

    def _analyze_with_roboflow(self, image_bytes: bytes) -> dict:
        import base64 as b64
        try:
            b64_img = b64.b64encode(image_bytes).decode("utf-8")
            result = self._roboflow_client.infer(
                b64_img,
                model_id=self._roboflow_model_id,
            )
            predictions = result.get("predictions", [])
        except Exception:
            logger.exception("Roboflow cloud inference failed")
            return self._build_error("roboflow_error")

        all_detections = []
        persons_raw = []
        violations_raw = []

        for pred in predictions:
            class_name = pred.get("class", "")
            conf = pred.get("confidence", 0)
            x = pred.get("x", 0)
            y = pred.get("y", 0)
            w = pred.get("width", 0)
            h = pred.get("height", 0)
            xyxy = [x - w / 2, y - h / 2, x + w / 2, y + h / 2]
            mapped = self._map_class(class_name)

            det = {
                "class_name": class_name,
                "mapped_class": mapped,
                "confidence": round(conf * 100, 1),
                "bbox": [round(v, 1) for v in xyxy],
            }
            all_detections.append(det)

            if self._is_person(class_name):
                persons_raw.append(det)
            if mapped in _NEGATIVE_CLASSES:
                violations_raw.append(det)

        return self._build_result(all_detections, persons_raw, violations_raw)

    def _build_result(self, all_detections, persons_raw, violations_raw):
        persons: list[PersonDetection] = []
        for idx, person in enumerate(persons_raw):
            ppe_items = []
            ppe_classes = []
            px1, py1, px2, py2 = person["bbox"]

            for det in all_detections:
                if self._is_person(det["class_name"]):
                    continue
                mapped = det["mapped_class"]
                if not self._is_ppe_positive(mapped):
                    continue
                dx1, dy1, dx2, dy2 = det["bbox"]
                cx = (dx1 + dx2) / 2
                cy = (dy1 + dy2) / 2
                if px1 <= cx <= px2 and py1 <= cy <= py2:
                    ppe_items.append(PPEItem(
                        class_name=mapped,
                        confidence=det["confidence"],
                        bbox=det["bbox"],
                    ))
                    ppe_classes.append(mapped)

            for viol in violations_raw:
                dx1, dy1, dx2, dy2 = viol["bbox"]
                cx = (dx1 + dx2) / 2
                cy = (dy1 + dy2) / 2
                if px1 <= cx <= px2 and py1 <= cy <= py2:
                    mapped = viol["mapped_class"]
                    if mapped == "head" and "hardhat" not in ppe_classes:
                        pass
                    elif mapped == "no_vest" and "safety_vest" not in ppe_classes:
                        pass

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
            mapped = det["mapped_class"]
            if not self._is_ppe_positive(mapped):
                continue
            if mapped not in ppe_summary:
                ppe_summary[mapped] = 0
            ppe_summary[mapped] += 1

        return {
            "status": "success",
            "total_persons": total_persons,
            "compliant_persons": compliant_persons,
            "compliance_rate": compliance_rate,
            "persons": [p.model_dump() for p in persons],
            "all_detections": all_detections,
            "ppe_summary": ppe_summary,
            "model_source": self._model_source,
        }

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
