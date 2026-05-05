import logging
import json
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import Settings

logger = logging.getLogger(__name__)


def classify_intent(transcription: str, settings: Settings) -> dict[str, Any]:
    """
    Sends transcription to DeepSeek V3.2 to classify user intent.
    
    Returns a dict with:
    - intent: str (the detected intent)
    - confidence: float (0-1)
    - should_call_rms: bool (whether to query Resource Management Service)
    - summary: str (brief description of the intent)
    - user_message: str (message to show to user)
    """
    
    # System prompt for intent classification
    system_prompt = """You are an expert intent classifier for a cloud services management assistant.
Analyze user transcriptions and determine their intent with high precision.

CLASSIFICATION RULES:
1. If the user wants to check/query/see/show their current services/resources/status, classify as: "query_services"
   Examples: "How are my services", "What is the status of my services", "Show me my current services", 
             "List my resources", "Check my services", "What services do I have"
2. If the user wants to check/query their monthly billing info, expenses, or spend, classify as: "query_billing"
   Examples: "Please give me the billing info of March 2026", "cuánto gasté en marzo de 2026", "What is my bill for last month"
   - You MUST extract the `bill_cycle` in `YYYY-MM` format (e.g. "2026-03").
   - You MUST extract the `language` of the user's input: "en" or "es".
3. For any other intent that is not supported yet, classify as: "unsupported"

Return ONLY a valid JSON object (no markdown, no code blocks) with this exact structure:
{
    "intent": "query_services" or "query_billing" or "unsupported",
    "confidence": 0.0 to 1.0,
    "should_call_rms": true if "query_services", else false,
    "should_call_bss": true if "query_billing", else false,
    "bill_cycle": "YYYY-MM" (only if intent is query_billing),
    "language": "en" or "es",
    "summary": "brief description of what the user wants",
    "user_message": "message explaining what will be done or why it's not supported"
}

IMPORTANT:
- Always return valid JSON only
- Be conservative with confidence scores (0.7+ for high confidence)
- If you're uncertain, keep confidence below 0.7 and set should_call_rms/should_call_bss to false
"""

    url = settings.maas_api_url
    api_key = settings.maas_api_key

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    request_body = {
        "model": "deepseek-v3.2",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User said: {transcription}"},
        ],
        "thinking": {
            "type": "disabled"
        },
    }

    try:
        response = httpx.post(url, json=request_body, headers=headers, timeout=60.0, verify=False)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.exception("Failed to reach DeepSeek MaaS API")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to classify intent. DeepSeek API unreachable.",
        ) from exc

    try:
        response_data = response.json()
        # Extract content from the message
        if response_data.get("choices") and len(response_data["choices"]) > 0:
            message_content = response_data["choices"][0].get("message", {}).get("content", "")
            
            # Parse JSON from response
            result = json.loads(message_content)
            return result
        else:
            raise ValueError("Unexpected response format from DeepSeek")
    except (json.JSONDecodeError, ValueError, KeyError) as exc:
        logger.exception("Failed to parse DeepSeek response")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to parse intent classification response.",
        ) from exc
