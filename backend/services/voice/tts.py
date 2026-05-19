import asyncio
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import HTTPException, status

from config.settings import Settings
from config.logging import get_logger

logger = get_logger("services.voice.tts")


def _build_speech_payload(
    text: str,
    settings: Settings,
    voice: str | None = None,
    lang_code: str | None = None,
    speed: float | None = None,
) -> dict[str, Any]:
    return {
        "model": "kokoro",
        "input": text,
        "voice": voice or settings.kokoro_voice,
        "response_format": settings.kokoro_response_format,
        "download_format": settings.kokoro_response_format,
        "speed": speed or settings.kokoro_speed,
        "stream": False,
        "return_download_link": False,
        "lang_code": lang_code or settings.kokoro_lang_code,
        "volume_multiplier": 1,
        "normalization_options": {
            "normalize": True,
            "unit_normalization": False,
            "url_normalization": True,
            "email_normalization": True,
            "optional_pluralization_normalization": True,
            "phone_normalization": True,
            "replace_remaining_symbols": True,
        },
    }


def generate_speech(
    text: str,
    settings: Settings,
    voice: str | None = None,
    lang_code: str | None = None,
    speed: float | None = None,
) -> bytes:
    if not text or not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty text provided for TTS.",
        )

    url = settings.kokoro_speech_url
    if not url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kokoro TTS URL not configured. Set KOKORO_SPEECH_URL in .env",
        )

    payload = _build_speech_payload(text, settings, voice, lang_code, speed)
    last_error: Exception | None = None

    for attempt in range(1, settings.kokoro_max_retries + 1):
        try:
            started = time.perf_counter()
            response = httpx.post(
                url,
                json=payload,
                timeout=settings.kokoro_timeout,
            )
            elapsed_ms = int((time.perf_counter() - started) * 1000)

            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                if "audio" in content_type or "octet-stream" in content_type:
                    audio_bytes = response.content
                    logger.info(
                        "Kokoro TTS success",
                        extra={"structured_extra": {
                            "text_len": len(text),
                            "audio_bytes": len(audio_bytes),
                            "elapsed_ms": elapsed_ms,
                            "attempt": attempt,
                        }},
                    )
                    return audio_bytes

                logger.warning(
                    "Kokoro returned 200 but unexpected content-type: %s",
                    content_type,
                )
                return response.content

            if response.status_code >= 500:
                last_error = Exception(f"Kokoro server error {response.status_code}")
                logger.warning(
                    "Kokoro TTS server error (attempt %d/%d): %d",
                    attempt,
                    settings.kokoro_max_retries,
                    response.status_code,
                )
                continue

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Kokoro TTS error: {response.status_code} {response.text[:200]}",
            )

        except httpx.TimeoutException as exc:
            last_error = exc
            logger.warning(
                "Kokoro TTS timeout (attempt %d/%d): %.1fs",
                attempt,
                settings.kokoro_max_retries,
                settings.kokoro_timeout,
            )
            continue

        except httpx.ConnectError as exc:
            last_error = exc
            logger.warning(
                "Kokoro TTS connection error (attempt %d/%d): %s",
                attempt,
                settings.kokoro_max_retries,
                str(exc),
            )
            continue

        except HTTPException:
            raise

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Kokoro TTS failed after {settings.kokoro_max_retries} attempts: {str(last_error)}",
    )


async def generate_speech_async(
    text: str,
    settings: Settings,
    voice: str | None = None,
    lang_code: str | None = None,
    speed: float | None = None,
) -> bytes:
    return await asyncio.to_thread(
        generate_speech, text, settings, voice, lang_code, speed
    )


def check_kokoro_health(settings: Settings) -> dict[str, Any]:
    url = settings.kokoro_speech_url
    if not url:
        return {"available": False, "reason": "KOKORO_SPEECH_URL not configured"}

    health_url = url.rsplit("/v1/audio/speech", 1)[0].rstrip("/") + "/health"
    try:
        response = httpx.get(health_url, timeout=5.0)
        if response.is_success:
            return {"available": True, "status": response.json()}
        return {"available": False, "status_code": response.status_code}
    except Exception as exc:
        return {"available": False, "reason": str(exc)}
