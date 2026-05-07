import base64
import logging
from pathlib import Path
from typing import Any

import httpx
from fastapi import HTTPException, status

from config.settings import Settings

logger = logging.getLogger(__name__)


def _build_iam_auth_payload(settings: Settings) -> dict[str, Any]:
    return {
        "auth": {
            "identity": {
                "methods": ["password"],
                "password": {
                    "user": {
                        "name": settings.huawei_username,
                        "password": settings.huawei_password,
                        "domain": {"name": settings.huawei_domain_name},
                    }
                },
            },
            "scope": {"project": {"id": settings.huawei_project_id}},
        }
    }


def get_iam_token(settings: Settings) -> str:
    iam_url = f"{settings.huawei_iam_endpoint.rstrip('/')}/v3/auth/tokens"
    payload = _build_iam_auth_payload(settings)

    try:
        response = httpx.post(iam_url, json=payload, timeout=20.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.exception("Failed to obtain Huawei IAM token")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to obtain Huawei IAM token. Check IAM endpoint and credentials.",
        ) from exc

    token = response.headers.get("X-Subject-Token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="IAM response did not include X-Subject-Token.",
        )
    return token


def _extract_transcript(sis_payload: dict[str, Any]) -> str:
    if isinstance(sis_payload.get("result"), dict):
        return str(sis_payload["result"].get("text", "")).strip()
    if isinstance(sis_payload.get("result"), list) and sis_payload["result"]:
        first = sis_payload["result"][0]
        if isinstance(first, dict):
            return str(first.get("text", "")).strip()
    return str(sis_payload.get("text", "")).strip()


def _candidate_properties(settings: Settings) -> list[str]:
    primary = settings.sis_property.strip()
    fallbacks = [p.strip() for p in settings.sis_fallback_properties.split(",") if p.strip()]
    props: list[str] = []
    for prop in [primary, *fallbacks]:
        if prop and prop not in props:
            props.append(prop)
    return props


def transcribe_short_audio(audio_path: Path, settings: Settings) -> dict[str, Any]:
    token = get_iam_token(settings)
    sis_url = f"{settings.huawei_sis_endpoint.rstrip('/')}/v1/{settings.huawei_project_id}/asr/short-audio"

    with audio_path.open("rb") as file_obj:
        audio_bytes = file_obj.read()
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    headers = {
        "X-Auth-Token": token,
        "Content-Type": "application/json",
    }

    last_error_response: str | None = None
    successful_property: str | None = None
    payload: dict[str, Any] | None = None
    for property_name in _candidate_properties(settings):
        request_body = {
            "data": audio_b64,
            "config": {
                "audio_format": "wav",
                "property": property_name,
                "add_punc": settings.sis_add_punc,
                "digit_norm": settings.sis_digit_norm,
                "need_word_info": settings.sis_need_word_info,
            },
        }
        try:
            response = httpx.post(sis_url, json=request_body, headers=headers, timeout=60.0)
        except httpx.HTTPError as exc:
            logger.exception("Failed to reach Huawei SIS")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not reach Huawei SIS endpoint.",
            ) from exc

        if response.is_success:
            payload = response.json()
            successful_property = property_name
            break

        body_text = response.text
        last_error_response = f"{response.status_code} {body_text}"
        if response.status_code == 400 and "SIS.0032" in body_text:
            logger.warning("SIS property '%s' rejected. Trying next.", property_name)
            continue

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Huawei SIS error: {response.status_code} {body_text}",
        )

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "All configured SIS properties were rejected (SIS.0032). "
                f"Tried: {_candidate_properties(settings)}. "
                f"Last provider response: {last_error_response}. "
                "Set SIS_PROPERTY (and optional SIS_FALLBACK_PROPERTIES) "
                "to values valid for your region/account."
            ),
        )

    return {
        "text": _extract_transcript(payload),
        "request_id": response.headers.get("X-Request-Id"),
        "audio_format": f"wav ({successful_property})",
        "audio_size_bytes": len(audio_bytes),
        "provider_raw_response": payload,
    }
