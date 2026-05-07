import logging
from pathlib import Path

import httpx
from fastapi import HTTPException, status

from config.settings import Settings

logger = logging.getLogger(__name__)


def transcribe_spanish_audio(audio_path: Path, settings: Settings) -> dict:
    url = settings.whisper_asr_url
    params = {
        "encode": "true",
        "task": "transcribe",
        "language": "es",
        "output": "txt",
    }

    try:
        with open(audio_path, "rb") as f:
            files = {"audio_file": (audio_path.name, f, "audio/wav")}
            headers = {"accept": "application/json"}
            response = httpx.post(url, params=params, files=files, headers=headers, timeout=60.0)
            response.raise_for_status()
            text = response.text.strip()

            return {
                "text": text,
                "request_id": response.headers.get("x-request-id", "whisper-local"),
                "audio_format": "wav (whisper_es)",
                "audio_size_bytes": audio_path.stat().st_size,
                "provider_raw_response": {"text": text},
            }
    except httpx.HTTPError as exc:
        logger.exception("Failed to reach Whisper ASR API")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Whisper API error: {str(exc)}",
        )
