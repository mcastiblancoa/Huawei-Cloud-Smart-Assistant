import logging

logger = logging.getLogger(__name__)

logger.warning(
    "services.intent is deprecated. Voice pipeline now routes through the "
    "central chat agent (api.chat.run_chat_turn). This module is kept as a "
    "stub for backward compatibility only."
)


def classify_intent(transcription: str, settings) -> dict:
    raise NotImplementedError(
        "Intent classification is deprecated. Use run_chat_turn() from api.chat instead."
    )
