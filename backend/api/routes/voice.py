import base64
import time
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from config.settings import get_settings
from config.logging import get_logger
from models.schemas import VoiceResponse
from services.voice import (
    validate_upload, save_upload, convert_to_wav_16k_mono,
    transcribe_short_audio, transcribe_spanish_audio,
    generate_speech,
)
from api.chat import run_chat_turn

logger = get_logger("api.voice")
router = APIRouter()
settings = get_settings()


@router.post("/voice")
async def voice_turn(
    file: UploadFile = File(...),
    language: str = Form("en"),
    session_id: str = Form(""),
) -> JSONResponse:
    validate_upload(file, max_size_mb=settings.max_upload_mb)
    temp_dir = Path(settings.temp_dir)
    original_file_path = save_upload(file, temp_dir=temp_dir)
    converted_path = None

    try:
        logger.info(
            "Voice turn: audio=%s, language=%s, session=%s",
            original_file_path.name, language, session_id,
        )
        converted_path = convert_to_wav_16k_mono(original_file_path, temp_dir=temp_dir)

        if language == "es":
            stt_result = transcribe_spanish_audio(converted_path, settings)
        else:
            stt_result = transcribe_short_audio(converted_path, settings)

        transcription = (stt_result.get("text") or "").strip()
        if not transcription:
            return JSONResponse(content=VoiceResponse(
                transcription="",
                reply="",
                session_id=session_id,
                error="Could not transcribe audio. Please try again.",
            ).model_dump())

        logger.info("STT result: %s", transcription[:100])

        if not session_id:
            from uuid import uuid4
            session_id = f"voice-{uuid4().hex[:12]}"

        agent_result = run_chat_turn(transcription, session_id)
        reply = agent_result.get("reply", "")

        audio_b64: str | None = None
        tts_error: str | None = None
        if reply and settings.kokoro_speech_url:
            try:
                tts_lang = "es" if language == "es" else "en"
                audio_bytes = generate_speech(reply, settings, lang_code=tts_lang)
                audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
            except Exception as exc:
                tts_error = str(exc)
                logger.warning("TTS generation failed: %s", tts_error)

        voice_resp = VoiceResponse(
            transcription=transcription,
            reply=reply,
            session_id=session_id,
            has_audio=audio_b64 is not None,
            latency_ms=agent_result.get("latency_ms"),
            tool_calls=agent_result.get("tool_calls"),
            path=agent_result.get("path"),
            error=tts_error,
        )

        payload = voice_resp.model_dump()
        if audio_b64:
            payload["audio_base64"] = audio_b64
            payload["audio_format"] = settings.kokoro_response_format

        return JSONResponse(content=payload)

    except Exception as exc:
        logger.exception("Voice turn error")
        return JSONResponse(
            content=VoiceResponse(
                transcription="",
                reply="",
                session_id=session_id,
                error=str(exc),
            ).model_dump(),
            status_code=500,
        )

    finally:
        for path in [original_file_path, converted_path]:
            if path and path.exists():
                path.unlink(missing_ok=True)


@router.post("/transcribe")
def transcribe_legacy(
    file: UploadFile = File(...),
    language: str = Form("en"),
) -> dict:
    validate_upload(file, max_size_mb=settings.max_upload_mb)
    temp_dir = Path(settings.temp_dir)
    original_file_path = save_upload(file, temp_dir=temp_dir)
    converted_path = None

    try:
        logger.info("Legacy transcribe: audio=%s, language=%s", original_file_path.name, language)
        converted_path = convert_to_wav_16k_mono(original_file_path, temp_dir=temp_dir)

        if language == "es":
            result = transcribe_spanish_audio(converted_path, settings)
        else:
            result = transcribe_short_audio(converted_path, settings)

        return {
            "text": result.get("text", ""),
            "request_id": result.get("request_id"),
            "audio_format": result.get("audio_format", ""),
            "audio_size_bytes": result.get("audio_size_bytes", 0),
            "provider_raw_response": result.get("provider_raw_response", {}),
        }
    finally:
        for path in [original_file_path, converted_path]:
            if path and path.exists():
                path.unlink(missing_ok=True)
