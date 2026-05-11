import time
from typing import Any

from langchain_core.messages import BaseMessage

from agents.graph import build_graph
from orchestration import run_fast_path
from observability import Tracer, MetricsCollector
from config.logging import get_logger
from config.settings import get_settings

logger = get_logger("api.chat")

_graph_instance = None
_settings = get_settings()


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


def _detect_language(text: str) -> str:
    spanish_tokens = {"que", "cual", "cuanto", "recursos", "gasto", "factura", "como", "donde", "cuando", "por que", "lista", "muestra", "dime", "ver", "hay", "tiene", "hola", "gracias", "abril", "mayo", "marzo"}
    lower = text.lower().split()
    if any(t in spanish_tokens for t in lower):
        return "es"
    return "en"


def run_chat_turn(user_input: str, session_id: str) -> dict[str, Any]:
    metrics = MetricsCollector.get()
    tracer = Tracer.get()

    span = tracer.start_span("chat_turn", {"session_id": session_id, "input_len": len(user_input)})
    started = time.perf_counter()

    language = _detect_language(user_input)

    fast_reply = run_fast_path(user_input, language, session_id=session_id)
    if fast_reply:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        tracer.end_span("chat_turn", "ok")
        metrics.record_request(elapsed_ms, is_fast_path=True, tool_calls=1)
        logger.info("Fast path reply", extra={"structured_extra": {
            "session_id": session_id, "elapsed_ms": elapsed_ms,
        }})
        return {
            "reply": fast_reply,
            "raw_messages": [],
            "latency_ms": elapsed_ms,
            "tool_calls": 1,
            "path": "fast",
        }

    graph = _get_graph()
    max_iterations = _settings.max_graph_iterations

    iteration_count = 0
    tool_call_count = 0
    messages = []

    for event in graph.stream(
        {"messages": [{"role": "user", "content": user_input}]},
        config={"configurable": {"thread_id": session_id}},
        stream_mode="values",
    ):
        iteration_count += 1
        messages = event.get("messages", [])

        if messages:
            last = messages[-1]
            if hasattr(last, "tool_calls") and last.tool_calls:
                tool_call_count += len(last.tool_calls)

        if iteration_count >= max_iterations:
            logger.warning("Max iterations reached (%d)", max_iterations)
            break

    reply = _extract_reply(messages)

    if not reply:
        for message in reversed(messages):
            msg_type = getattr(message, "type", None)
            if msg_type == "ai":
                content = getattr(message, "content", "")
                if content:
                    reply = str(content).strip()
                    break

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    tracer.end_span("chat_turn", "ok")
    metrics.record_request(elapsed_ms, is_fast_path=False, tool_calls=tool_call_count)
    metrics.record_llm_call()

    logger.info("Chat turn completed", extra={"structured_extra": {
        "session_id": session_id,
        "reply_len": len(reply),
        "iterations": iteration_count,
        "tool_calls": tool_call_count,
        "elapsed_ms": elapsed_ms,
    }})

    return {
        "reply": reply or "No response generated.",
        "raw_messages": _serialize_messages(messages) if messages else [],
        "latency_ms": elapsed_ms,
        "tool_calls": tool_call_count,
        "path": "llm",
    }
