import json
import time
from typing import Any

import httpx

from config.settings import get_settings
from config.logging import get_logger
from utils.sanitize import sanitize_model_reply

logger = get_logger("orchestration.llm_formatter")

_settings = get_settings()


def format_with_llm(context: str, user_query: str, language: str, timeout: float = 30.0) -> str:
    url = _settings.maas_api_url
    api_key = _settings.maas_api_key

    if not url or not api_key:
        return context

    lang_name = "español" if language == "es" else "English"
    lang_rule = (
        "OBLIGATORIO: escribe TODO el mensaje final en español. No uses inglés ni mezclas idiomas."
        if language == "es"
        else "OBLIGATORIO: write the entire reply in English only."
    )

    system_prompt = f"""Eres un asistente de Huawei Cloud. {lang_rule} (Idioma objetivo: {lang_name}.)
REGLAS:
- Usa SOLO los datos proporcionados. NUNCA inventes información.
- Si los datos muestran 0 recursos, di claramente que no se encontraron recursos.
- Sé breve: un párrafo o dos en prosa, solo lo esencial (nombres, regiones, estados, montos cuando aplique).
- Sin tablas, sin listas numeradas, sin viñetas largas.
- Sin color ni spans con estilo; para destacar datos importantes usa solo <strong>valor</strong>.
- NO digas "Voy a consultar", "Déjame verificar", ni nombres de herramientas internas. Solo presenta la información."""

    user_prefix = (
        "[El usuario escribe en español.]\n\n" if language == "es" else "[The user writes in English.]\n\n"
    )

    request_body = {
        "model": _settings.intent_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{user_prefix}Pregunta del usuario: {user_query}\n\nDatos reales obtenidos:\n{context}"},
        ],
        "thinking": {"type": "disabled"},
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    try:
        started = time.perf_counter()
        response = httpx.post(url, json=request_body, headers=headers, timeout=timeout, verify=False)
        response.raise_for_status()
        elapsed = int((time.perf_counter() - started) * 1000)
        data = response.json()
        if data.get("choices") and len(data["choices"]) > 0:
            content = data["choices"][0].get("message", {}).get("content", "").strip()
            if content:
                logger.info("LLM formatting OK", extra={"structured_extra": {"elapsed_ms": elapsed}})
                return sanitize_model_reply(content)
        return context
    except Exception as exc:
        logger.warning("LLM formatting failed: %s", str(exc)[:100])
        return context
