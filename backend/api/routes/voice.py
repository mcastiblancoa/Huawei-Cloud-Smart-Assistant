from pathlib import Path

from fastapi import APIRouter, File, UploadFile, Form

from config.settings import get_settings
from models.schemas import (
    TranscriptionResponse, IntentClassification, ResourcesResponse, BillingSummary,
)
from services.voice import validate_upload, save_upload, convert_to_wav_16k_mono, transcribe_short_audio, transcribe_spanish_audio
from services.intent import classify_intent
from services.resources import list_all_resources
from services.billing import get_monthly_billing_summary, generate_natural_billing_response
from config.logging import get_logger

logger = get_logger("api.voice")
router = APIRouter()
settings = get_settings()


@router.post("/transcribe", response_model=TranscriptionResponse)
def transcribe(
    file: UploadFile = File(...),
    language: str = Form("en"),
) -> TranscriptionResponse:
    validate_upload(file, max_size_mb=settings.max_upload_mb)
    temp_dir = Path(settings.temp_dir)
    original_file_path = save_upload(file, temp_dir=temp_dir)
    converted_path = None
    try:
        logger.info("Received audio: %s, language: %s", original_file_path.name, language)
        converted_path = convert_to_wav_16k_mono(original_file_path, temp_dir=temp_dir)

        if language == "es":
            result = transcribe_spanish_audio(converted_path, settings)
        else:
            result = transcribe_short_audio(converted_path, settings)

        transcription_response = TranscriptionResponse(**result)

        if transcription_response.text and transcription_response.text.strip():
            logger.info("Classifying intent from transcription: %s", transcription_response.text[:100])
            try:
                intent_data = classify_intent(transcription_response.text, settings)
                transcription_response.intent_classification = IntentClassification(**intent_data)
                logger.info("Intent classified: %s (confidence: %.2f)", intent_data.get("intent"), intent_data.get("confidence", 0))

                if intent_data.get("should_call_rms", False):
                    logger.info("Fetching resources from Huawei Cloud RMS")
                    try:
                        resources_data = list_all_resources(settings)
                        transcription_response.resources_response = ResourcesResponse(**resources_data)
                        logger.info("Successfully fetched %d resources", resources_data.get("total", 0))
                    except Exception as exc:
                        logger.error("Failed to fetch resources: %s", str(exc))
                        transcription_response.resources_response = ResourcesResponse(total=0, resources=[], error=str(exc))

                if intent_data.get("should_call_bss", False) and intent_data.get("bill_cycle"):
                    logger.info("Fetching billing summary from Huawei Cloud BSS")
                    try:
                        bill_cycle = intent_data["bill_cycle"]
                        lang = intent_data.get("language", "en")
                        billing_data = get_monthly_billing_summary(settings, bill_cycle)
                        if not billing_data.get("error"):
                            natural_res = generate_natural_billing_response(settings, billing_data, lang)
                            billing_data["natural_response"] = natural_res
                        transcription_response.billing_response = BillingSummary(**billing_data)
                        logger.info("Successfully fetched billing summary")
                    except Exception as exc:
                        logger.error("Failed to fetch billing data: %s", str(exc))
                        transcription_response.billing_response = BillingSummary(
                            month=intent_data["bill_cycle"], total=0.0, currency="USD", services=[], error=str(exc),
                        )
            except Exception as exc:
                logger.error("Failed to classify intent: %s", str(exc))

        return transcription_response
    finally:
        for path in [original_file_path, converted_path]:
            if path and path.exists():
                path.unlink(missing_ok=True)
