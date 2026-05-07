from functools import lru_cache
from typing import Any

from langchain_core.messages import BaseMessage

from agents.graph import build_graph
from config.logging import get_logger

logger = get_logger("api.chat")

_graph_instance = None


def _get_graph():
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = build_graph()
    return _graph_instance


def _extract_reply(messages: list[BaseMessage | dict[str, Any]]) -> str:
    for message in reversed(messages):
        message_type = getattr(message, "type", None)
        if message_type == "ai":
            content = getattr(message, "content", "")
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        parts.append(item.get("text", ""))
                content = "\n".join(part for part in parts if part).strip()
            return str(content).strip()
        if isinstance(message, dict) and message.get("type") == "ai":
            return str(message.get("content", "")).strip()
    return ""


def _serialize_messages(messages: list[BaseMessage]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for message in messages:
        serialized.append({
            "type": getattr(message, "type", message.__class__.__name__.lower()),
            "content": getattr(message, "content", ""),
        })
    return serialized


def run_chat_turn(user_input: str, session_id: str) -> dict[str, Any]:
    graph = _get_graph()
    logger.info(
        "Running chat turn",
        extra={"structured_extra": {"session_id": session_id, "input_len": len(user_input)}},
    )

    result = graph.invoke(
        {"messages": [{"role": "user", "content": user_input}]},
        config={"configurable": {"thread_id": session_id}},
    )
    messages = result.get("messages", [])
    reply = _extract_reply(messages)

    logger.info(
        "Chat turn completed",
        extra={"structured_extra": {"session_id": session_id, "reply_len": len(reply)}},
    )

    return {
        "reply": reply or "No response generated.",
        "raw_messages": _serialize_messages(messages) if messages else [],
    }
