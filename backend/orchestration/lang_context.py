"""Per-request language for chat (fast path + LangGraph) via contextvars."""

from contextvars import ContextVar

current_chat_language: ContextVar[str] = ContextVar("current_chat_language", default="en")
