import base64
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
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
    "hard_hat": "hardhat",
    "hard-hat": "hardhat",
    "bump cap": "hardhat",
    "head": "head",
    "no hardhat": "head",
    "no-hard hat": "head",
    "no-hardhat": "head",
    "no helmet": "head",
    "no-hard hat": "head",
    "NO-Hardhat": "head",
    "safety_vest": "safety_vest",
    "safety vest": "safety_vest",
    "vest": "safety_vest",
    "reflective vest": "safety_vest",
    "reflective_vest": "safety_vest",
    "hi-vis vest": "safety_vest",
    "hi-vis": "safety_vest",
    "high-visibility vest": "safety_vest",
    "high_visibility_vest": "safety_vest",
    "hiviz vest": "safety_vest",
    "no vest": "no_vest",
    "no-safety vest": "no_vest",
    "no_safety_vest": "no_vest",
    "NO-Safety Vest": "no_vest",
    "goggles": "goggles",
    "glasses": "goggles",
    "safety glasses": "goggles",
    "safety_glasses": "goggles",
    "face_shield": "face_shield",
    "face shield": "face_shield",
    "mask": "mask",
    "gloves": "gloves",
    "safety_boots": "safety_boots",
    "safety boots": "safety_boots",
    "boots": "safety_boots",
    "safety shoes": "safety_boots",
    "safety_shoes": "safety_boots",
}

_NEGATIVE_CLASSES = {
    "no hardhat", "no-hard hat", "no-hardhat", "no helmet",
    "no vest", "no-safety vest", "no_safety_vest",
    "NO-Hardhat", "NO-Safety Vest",
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
        self._is_coco_fallback = False

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
                self._is_coco_fallback = False
                self._initialized = True
                logger.info("PPE model loaded successfully — dedicated hardhat/vest detection")
                return True
            except Exception as exc:
                logger.warning("Failed to load PPE model (%s: %s)", type(exc).__name__, exc)

        if self._try_roboflow():
            self._initialized = True
            self._is_coco_fallback = False
            return True

        try:
            from ultralytics import YOLO
            logger.info("Loading fallback COCO model: yolov8n.pt")
            self._model = YOLO("yolov8n.pt")
            self._model_source = "yolov8n-coco"
            self._is_coco_fallback = True
            self._initialized = True
            logger.warning(
                "COCO model loaded — PPE detection will use color-based heuristics. "
                "For best results, run: python download_ppe_model.py"
            )
            return True
        except Exception as exc:
            logger.warning("Ultralytics not available (%s: %s)", type(exc).__name__, exc)

        self._initialized = True
        self._model = None
        self._is_coco_fallback = False
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
            return self._analyze_with_yolo(tmp_path, image_bytes)
        except Exception:
            logger.exception("Error analyzing safety frame")
            return self._build_error("processing_error")
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _analyze_with_yolo(self, image_path: str, image_bytes: bytes = None) -> dict:
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

        if self._is_coco_fallback and image_bytes and persons_raw:
            color_detections = self._detect_ppe_by_color(image_bytes, persons_raw)
            all_detections.extend(color_detections)

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

    def _detect_ppe_by_color(self, image_bytes: bytes, persons_raw: list) -> list:
        try:
            import cv2
        except ImportError:
            logger.debug("OpenCV not available for color-based PPE detection")
            return []

        try:
            arr = np.frombuffer(image_bytes, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                return []
        except Exception:
            logger.debug("Failed to decode image for color analysis")
            return []

        h, w = img.shape[:2]
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        detections = []

        hardhat_lower = [
            (0, 50, 180),
            (10, 50, 180),
            (170, 50, 180),
            (20, 60, 160),
        ]
        hardhat_upper = [
            (10, 255, 255),
            (25, 255, 255),
            (180, 255, 255),
            (35, 255, 255),
        ]

        vest_lower = [
            (0, 60, 160),
            (10, 60, 160),
            (170, 60, 160),
            (20, 70, 150),
            (35, 60, 150),
        ]
        vest_upper = [
            (10, 255, 255),
            (25, 255, 255),
            (180, 255, 255),
            (35, 255, 255),
            (85, 255, 255),
        ]

        hardhat_mask = np.zeros((h, w), dtype=np.uint8)
        for lo, hi in zip(hardhat_lower, hardhat_upper):
            hardhat_mask |= cv2.inRange(hsv, np.array(lo), np.array(hi))

        vest_mask = np.zeros((h, w), dtype=np.uint8)
        for lo, hi in zip(vest_lower, vest_upper):
            vest_mask |= cv2.inRange(hsv, np.array(lo), np.array(hi))

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        hardhat_mask = cv2.morphologyEx(hardhat_mask, cv2.MORPH_OPEN, kernel)
        hardhat_mask = cv2.morphologyEx(hardhat_mask, cv2.MORPH_CLOSE, kernel)
        vest_mask = cv2.morphologyEx(vest_mask, cv2.MORPH_OPEN, kernel)
        vest_mask = cv2.morphologyEx(vest_mask, cv2.MORPH_CLOSE, kernel)

        for person in persons_raw:
            px1, py1, px2, py2 = person["bbox"]
            px1i, py1i, px2i, py2i = int(px1), int(py1), int(px2), int(py2)
            px1i = max(0, min(px1i, w - 1))
            py1i = max(0, min(py1i, h - 1))
            px2i = max(0, min(px2i, w - 1))
            py2i = max(0, min(py2i, h - 1))

            person_h = py2i - py1i
            if person_h < 20:
                continue

            head_y1 = py1i
            head_y2 = py1i + int(person_h * 0.22)
            head_region = hardhat_mask[head_y1:head_y2, px1i:px2i]
            head_area = max(1, (head_y2 - head_y1) * (px2i - px1i))
            head_color_ratio = np.count_nonzero(head_region) / head_area

            if head_color_ratio > 0.15:
                conf = min(0.95, head_color_ratio * 2.0)
                detections.append({
                    "class_name": "hardhat",
                    "mapped_class": "hardhat",
                    "confidence": round(conf * 100, 1),
                    "bbox": [round(px1, 1), round(py1, 1), round(px2, 1), round(float(head_y2), 1)],
                })

            torso_y1 = py1i + int(person_h * 0.18)
            torso_y2 = py1i + int(person_h * 0.55)
            torso_region = vest_mask[torso_y1:torso_y2, px1i:px2i]
            torso_area = max(1, (torso_y2 - torso_y1) * (px2i - px1i))
            torso_color_ratio = np.count_nonzero(torso_region) / torso_area

            if torso_color_ratio > 0.12:
                conf = min(0.95, torso_color_ratio * 1.8)
                detections.append({
                    "class_name": "safety_vest",
                    "mapped_class": "safety_vest",
                    "confidence": round(conf * 100, 1),
                    "bbox": [round(px1, 1), round(float(torso_y1), 1), round(px2, 1), round(float(torso_y2), 1)],
                })

        if detections:
            logger.debug("Color-based PPE detection found %d items", len(detections))

        return detections

    def _build_result(self, all_detections, persons_raw, violations_raw):
        persons: list[PersonDetection] = []
        for idx, person in enumerate(persons_raw):
            ppe_items = []
            ppe_classes = []
            violations = []
            px1, py1, px2, py2 = person["bbox"]
            person_w = max(1, px2 - px1)
            person_h = max(1, py2 - py1)

            for det in all_detections:
                if self._is_person(det["class_name"]):
                    continue
                mapped = det["mapped_class"]
                if not self._is_ppe_positive(mapped):
                    continue
                dx1, dy1, dx2, dy2 = det["bbox"]
                cx = (dx1 + dx2) / 2
                cy = (dy1 + dy2) / 2

                if mapped == "hardhat":
                    head_y2 = py1 + person_h * 0.35
                    in_region = px1 <= cx <= px2 and py1 <= cy <= head_y2
                elif mapped == "safety_vest":
                    torso_y1 = py1 + person_h * 0.15
                    torso_y2 = py1 + person_h * 0.65
                    in_region = px1 <= cx <= px2 and torso_y1 <= cy <= torso_y2
                else:
                    in_region = px1 <= cx <= px2 and py1 <= cy <= py2

                if in_region:
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
                        violations.append("hardhat")
                    elif mapped == "no_vest" and "safety_vest" not in ppe_classes:
                        violations.append("safety_vest")

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
                compliant=len(missing) == 0 and len(violations) == 0,
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
            "is_coco_fallback": self._is_coco_fallback,
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
