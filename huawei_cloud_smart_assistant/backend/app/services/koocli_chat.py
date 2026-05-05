import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

# Resolve koocli-assitant directory relative to this file
# This file: backend/app/services/koocli_chat.py
# Root:      huawei_cloud_smart_assistant/
# Sibling:   koocli-assitant/
_huawei_dir = Path(__file__).resolve().parents[3]  # huawei_cloud_smart_assistant/
KOOCLI_DIR = _huawei_dir.parent / "koocli-assitant"
if str(KOOCLI_DIR) not in sys.path:
    sys.path.insert(0, str(KOOCLI_DIR))

from langchain_core.messages import BaseMessage

from graph import build_graph


@lru_cache(maxsize=1)
def _get_graph():
    return build_graph()


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
        serialized.append(
            {
                "type": getattr(message, "type", message.__class__.__name__.lower()),
                "content": getattr(message, "content", ""),
            }
        )
    return serialized


def run_chat_turn(user_input: str, session_id: str) -> dict[str, Any]:
    graph = _get_graph()
    result = graph.invoke(
        {"messages": [{"role": "user", "content": user_input}]},
        config={"configurable": {"thread_id": session_id}},
    )
    messages = result.get("messages", [])
    reply = _extract_reply(messages)
    return {
        "reply": reply or "No response generated.",
        "raw_messages": _serialize_messages(messages) if messages else [],
    }