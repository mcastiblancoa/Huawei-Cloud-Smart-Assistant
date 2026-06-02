import base64
import logging
import time

from fastapi import APIRouter, File, Form, UploadFile

from models.schemas import SentimentResponse, SafetyResponse
from services.vision.sentiment_service import SentimentService
from services.vision.safety_service import SafetyService
from config.logging import get_logger

logger = get_logger("api.vision_route")
router = APIRouter(prefix="/vision")

_sentiment_service = SentimentService()
_safety_service = SafetyService()


@router.get("/status")
async def vision_status():
    sentiment_backend = _sentiment_service._detector._ensure_initialized()
    safety_available = _safety_service._detector._ensure_initialized()
    return {
        "sentiment_backend": sentiment_backend,
        "safety_available": safety_available,
        "deepface_available": sentiment_backend == "deepface",
        "opencv_available": sentiment_backend in ("deepface", "opencv-haar"),
    }


@router.post("/sentiment", response_model=SentimentResponse)
async def analyze_sentiment(
    file: UploadFile = File(...),
) -> SentimentResponse:
    started_at = time.perf_counter()
    image_bytes = await file.read()

    logger.info(
        "Sentiment analysis request",
        extra={"structured_extra": {
            "filename": file.filename,
            "size_bytes": len(image_bytes),
        }},
    )

    result = _sentiment_service.analyze_image(image_bytes)

    total_ms = round((time.perf_counter() - started_at) * 1000)
    logger.info(
        "Sentiment analysis complete",
        extra={"structured_extra": {
            "status": result.get("status"),
            "dominant_emotion": result.get("dominant_emotion"),
            "face_count": result.get("face_count"),
            "latency_ms": total_ms,
        }},
    )

    return SentimentResponse(
        status=result.get("status", "error"),
        dominant_emotion=result.get("dominant_emotion"),
        confidence=result.get("confidence"),
        all_scores=result.get("all_scores"),
        faces=result.get("faces", []),
        face_count=result.get("face_count", 0),
        latency_ms=total_ms,
        error=result.get("error"),
    )


@router.post("/sentiment/base64", response_model=SentimentResponse)
async def analyze_sentiment_base64(
    image: str = Form(...),
) -> SentimentResponse:
    started_at = time.perf_counter()

    logger.info("Sentiment base64 analysis request")

    result = _sentiment_service.analyze_base64(image)

    total_ms = round((time.perf_counter() - started_at) * 1000)

    return SentimentResponse(
        status=result.get("status", "error"),
        dominant_emotion=result.get("dominant_emotion"),
        confidence=result.get("confidence"),
        all_scores=result.get("all_scores"),
        faces=result.get("faces", []),
        face_count=result.get("face_count", 0),
        latency_ms=total_ms,
        error=result.get("error"),
    )


@router.post("/safety", response_model=SafetyResponse)
async def analyze_safety(
    file: UploadFile = File(...),
) -> SafetyResponse:
    started_at = time.perf_counter()
    image_bytes = await file.read()

    logger.info(
        "Safety analysis request",
        extra={"structured_extra": {
            "filename": file.filename,
            "size_bytes": len(image_bytes),
        }},
    )

    result = _safety_service.analyze_image(image_bytes)

    total_ms = round((time.perf_counter() - started_at) * 1000)
    logger.info(
        "Safety analysis complete",
        extra={"structured_extra": {
            "status": result.get("status"),
            "total_persons": result.get("total_persons"),
            "compliance_rate": result.get("compliance_rate"),
            "latency_ms": total_ms,
        }},
    )

    return SafetyResponse(
        status=result.get("status", "error"),
        total_persons=result.get("total_persons", 0),
        compliant_persons=result.get("compliant_persons", 0),
        compliance_rate=result.get("compliance_rate", 0.0),
        persons=result.get("persons", []),
        all_detections=result.get("all_detections", []),
        ppe_summary=result.get("ppe_summary", {}),
        latency_ms=total_ms,
        error=result.get("error"),
    )
