"""Per-request language and voice mode for chat (fast path + LangGraph) via contextvars."""

from contextvars import ContextVar

current_chat_language: ContextVar[str] = ContextVar("current_chat_language", default="en")
is_voice_mode: ContextVar[bool] = ContextVar("is_voice_mode", default=False)
