import logging
import sys
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.models.schemas import ChatRequest, ChatResponse, HealthResponse, TranscriptionResponse, IntentClassification, ResourcesResponse, BillingSummary
from app.services.audio_processing import convert_to_wav_16k_mono, save_upload, validate_upload
from app.services.huawei_sis import transcribe_short_audio
from app.services.whisper_asr import transcribe_spanish_audio
from app.services.intent_classification import classify_intent
from app.services.huawei_rms import list_all_resources
from app.services.huawei_bss import get_monthly_billing_summary, generate_natural_billing_response

ROOT_DIR = Path(__file__).resolve().parents[4]
KOOCLI_DIR = ROOT_DIR / "koocli-assitant"
if str(KOOCLI_DIR) not in sys.path:
    sys.path.insert(0, str(KOOCLI_DIR))

from app.services.koocli_chat import run_chat_turn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("app.main")

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.backend_cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    result = run_chat_turn(request.message, request.session_id)
    return ChatResponse(
        session_id=request.session_id,
        reply=result["reply"],
        raw_messages=result.get("raw_messages"),
    )


@app.post("/transcribe", response_model=TranscriptionResponse)
def transcribe(
    file: UploadFile = File(...),
    language: str = Form("en")
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
        
        # Create base transcription response
        transcription_response = TranscriptionResponse(**result)
        
        # Step 1: Classify intent from transcription
        if transcription_response.text and transcription_response.text.strip():
            logger.info("Classifying intent from transcription: %s", transcription_response.text[:100])
            try:
                intent_data = classify_intent(transcription_response.text, settings)
                transcription_response.intent_classification = IntentClassification(**intent_data)
                logger.info("Intent classified: %s (confidence: %.2f)", 
                           intent_data.get("intent"), intent_data.get("confidence", 0))
                
                # Step 2: Query RMS if needed
                if intent_data.get("should_call_rms", False):
                    logger.info("Fetching resources from Huawei Cloud RMS")
                    try:
                        resources_data = list_all_resources(settings)
                        transcription_response.resources_response = ResourcesResponse(**resources_data)
                        logger.info("Successfully fetched %d resources", resources_data.get("total", 0))
                    except Exception as exc:
                        logger.error("Failed to fetch resources: %s", str(exc))
                        # Don't raise - still return the transcription with intent but without resources
                        transcription_response.resources_response = ResourcesResponse(
                            total=0,
                            resources=[],
                            error=str(exc)
                        )
                
                # Step 3: Query BSS if needed
                if intent_data.get("should_call_bss", False) and intent_data.get("bill_cycle"):
                    logger.info("Fetching billing summary from Huawei Cloud BSS")
                    try:
                        bill_cycle = intent_data["bill_cycle"]
                        lang = intent_data.get("language", "en")
                        billing_data = get_monthly_billing_summary(settings, bill_cycle)
                        if not billing_data.get("error"):
                            # Generate natural response
                            natural_res = generate_natural_billing_response(settings, billing_data, lang)
                            billing_data["natural_response"] = natural_res
                        transcription_response.billing_response = BillingSummary(**billing_data)
                        logger.info("Successfully fetched billing summary")
                    except Exception as exc:
                        logger.error("Failed to fetch billing data: %s", str(exc))
                        # Don't raise - still return the transcription with intent but without billing
                        transcription_response.billing_response = BillingSummary(
                            month=intent_data["bill_cycle"],
                            total=0.0,
                            currency="USD",
                            services=[],
                            error=str(exc)
                        )
            except Exception as exc:
                logger.error("Failed to classify intent: %s", str(exc))
                # Don't raise - still return transcription
                pass
        
        return transcription_response
    finally:
        for path in [original_file_path, converted_path]:
            if path and path.exists():
                path.unlink(missing_ok=True)
