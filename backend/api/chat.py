import re
import json
import time
import unicodedata
from typing import Any

from langchain_core.messages import BaseMessage, ToolMessage

from agents.graph import build_graph
from orchestration import run_fast_path
from orchestration.lang_context import current_chat_language, is_voice_mode
from observability import Tracer, MetricsCollector
from utils.sanitize import sanitize_model_reply
from config.logging import get_logger
from config.settings import get_settings

logger = get_logger("api.chat")

_graph_instance = None
_settings = get_settings()

# User explicitly asked for a language (e.g. "en español") — keep for the thread_id/session.
_SESSION_LANG: dict[str, str] = {}


def _get_graph():
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = build_graph()
    return _graph_instance


def _count_table_rows(table_md: str) -> int:
    lines = table_md.strip().split("\n")
    count = 0
    headers = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if re.match(r'^\|[-\s|:]+\|$', stripped):
            continue
        prev = lines[i - 1].strip() if i > 0 else ""
        if re.match(r'^\|[-\s|:]+\|$', prev):
            headers += 1
        else:
            count += 1
    return count


def _strip_markdown_tables(text: str) -> str:
    table_pattern = re.compile(r'\|[^\n]+\|\n\|[-\s|:]+\|\n(?:\|[^\n]+\|\n)*', re.MULTILINE)
    cleaned = table_pattern.sub('', text).strip()
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned


def _fix_counts_in_text(text: str, actual_count: int) -> str:
    if actual_count <= 0:
        return text
    text = re.sub(
        r'(?:<strong>|\*\*)?\b\d+\b(?:</strong>|\*\*)?\s+((?:instancia|instance|servidor|server|recurso|resource)s?|(?:ECS|EIP|VPC|ELB|RDS|SG))\b(?:</strong>|\*\*)?',
        lambda m: f'{actual_count} {m.group(1)}',
        text,
        flags=re.IGNORECASE,
    )
    return text


_ORPHAN_ROW_RE = re.compile(r'^\s*\|[^\n]+\|\s*$', re.MULTILINE)


def _strip_orphan_rows(text: str) -> str:
    return _ORPHAN_ROW_RE.sub('', text).strip()


def _replace_llm_table(reply: str, table_block: str) -> str:
    """Replace the LLM's markdown table with the tool's _table (more accurate).
    Fixes item counts in LLM text to match actual table rows."""
    actual_count = _count_table_rows(table_block)
    table_pattern = re.compile(r'\|[^\n]+\|\n\|[-\s|:]+\|\n(?:\|[^\n]+\|\n)+', re.MULTILINE)
    match = table_pattern.search(reply)
    if match:
        before = _strip_orphan_rows(reply[:match.start()].rstrip())
        before = _fix_counts_in_text(before, actual_count)
        after = _strip_orphan_rows(reply[match.end():].strip())
        parts = [before, table_block, after] if after else [before, table_block]
        return "\n\n".join(p for p in parts if p)
    reply = _fix_counts_in_text(reply, actual_count)
    reply = _strip_orphan_rows(reply)
    return reply + "\n\n" + table_block


_DEPLOY_DELETE_TOOL_NAMES = {
    "deploy_ecs_instance", "setup_elb_for_ecs", "create_rds_instance",
    "stop_ecs", "reboot_ecs", "release_eip", "delete_rds_instance",
    "manage_ecs", "manage_eip", "manage_obs_bucket",
    "associate_eip", "create_eip",
}

_AUXILIARY_TABLE_HEADERS = {"vpc", "subnet", "security group", "cidr"}


def _is_auxiliary_table(table_md: str) -> bool:
    header_line = table_md.strip().split("\n")[0].lower() if table_md.strip() else ""
    return any(h in header_line for h in _AUXILIARY_TABLE_HEADERS)


def _extract_tables_from_tools(messages: list[BaseMessage]) -> list[str]:
    tables = []
    seen = set()
    has_deploy_delete = False
    for message in messages:
        if isinstance(message, ToolMessage):
            name = getattr(message, "name", "") or ""
            if name in _DEPLOY_DELETE_TOOL_NAMES:
                has_deploy_delete = True
    for message in messages:
        if isinstance(message, ToolMessage):
            content = getattr(message, "content", "")
            if not isinstance(content, str) or not content:
                continue
            try:
                data = json.loads(content)
                table = data.get("_table", "")
                if table and isinstance(table, str) and "|" in table:
                    if has_deploy_delete and _is_auxiliary_table(table):
                        continue
                    key = table.strip()
                    if key not in seen:
                        seen.add(key)
                        tables.append(key)
            except (json.JSONDecodeError, TypeError):
                pass
    if len(tables) <= 1:
        return tables
    billing_months = []
    non_billing = []
    for t in tables:
        if "(USD)" in t:
            billing_months.append(t)
        else:
            non_billing.append(t)
    if len(billing_months) > 1:
        from tools.common.table_formatter import merge_billing_tables
        merged = merge_billing_tables(billing_months)
        return non_billing + [merged] if merged else non_billing + billing_months
    return tables


def _extract_billing_data_from_tools(messages: list[BaseMessage]) -> list[dict]:
    results = []
    for message in messages:
        if isinstance(message, ToolMessage):
            content = getattr(message, "content", "")
            if not isinstance(content, str) or not content:
                continue
            try:
                data = json.loads(content)
                if data.get("ok") and data.get("data") and isinstance(data["data"], dict):
                    d = data["data"]
                    if "month" in d and "services" in d:
                        results.append(d)
            except (json.JSONDecodeError, TypeError):
                pass
    return results


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


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def _detect_language(text: str) -> str:
    """Heuristic: Spanish punctuation, then token overlap (accent-insensitive)."""
    if any(ch in text for ch in "¿¡áéíóúüñÁÉÍÓÚÜÑ"):
        return "es"
    folded = _strip_accents(text.lower())
    tokens = set(re.findall(r"\w+", folded))
    spanish = {
        "que", "cual", "cuales", "cuantos", "cuanto", "recursos", "gasto", "factura", "como", "donde",
        "cuando", "porque", "lista", "muestra", "dime", "decirme", "ver", "hay", "tiene", "tienes",
        "tengo", "hola", "gracias", "servicios", "desplegados", "desplegado", "puedes", "puede",
        "podrias", "mismo", "ahora", "region", "instancia", "instancias", "ninguno", "ninguna",
        "crear", "borrar", "eliminar", "desplegar", "vpc", "redes", "seguridad", "balanceador",
    }
    if tokens & spanish:
        return "es"
    return "en"


def _apply_explicit_language_choice(session_id: str, text: str) -> None:
    tl = text.lower()
    if re.search(
        r"\b(en español|en espanol|en castellano|habla español|habla espanol|"
        r"respuesta[s]?\s+en\s+español|respuesta[s]?\s+en\s+espanol|idioma español|idioma espanol|español\b|espanol\b)",
        tl,
    ):
        _SESSION_LANG[session_id] = "es"
    elif re.search(r"\b(in english|english only|respuesta[s]?\s+en\s+ingl[eé]s|idioma ingl[eé]s)\b", tl):
        _SESSION_LANG[session_id] = "en"


def _resolve_language(session_id: str, text: str) -> str:
    _apply_explicit_language_choice(session_id, text)
    if session_id in _SESSION_LANG:
        return _SESSION_LANG[session_id]
    return _detect_language(text)


def run_chat_turn(user_input: str, session_id: str, is_voice: bool = False) -> dict[str, Any]:
    metrics = MetricsCollector.get()
    tracer = Tracer.get()

    span = tracer.start_span("chat_turn", {"session_id": session_id, "input_len": len(user_input)})
    started = time.perf_counter()

    language = _resolve_language(session_id, user_input)
    lang_token = current_chat_language.set(language)
    voice_token = is_voice_mode.set(is_voice)
    try:
        fast_reply = run_fast_path(user_input, language, session_id=session_id)
        if fast_reply:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            tracer.end_span("chat_turn", "ok")
            metrics.record_request(elapsed_ms, is_fast_path=True, tool_calls=1)
            logger.info("Fast path reply", extra={"structured_extra": {
                "session_id": session_id, "elapsed_ms": elapsed_ms,
            }})
            return {
                "reply": sanitize_model_reply(fast_reply),
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

        reply = sanitize_model_reply(reply) if reply else reply

        tool_tables = _extract_tables_from_tools(messages)
        if tool_tables:
            if is_voice:
                billing_data = _extract_billing_data_from_tools(messages)
                context_parts = []
                for t in tool_tables:
                    rows = _count_table_rows(t)
                    context_parts.append(f"Tabla con {rows} filas de datos:\n{t}")
                if billing_data:
                    from orchestration.llm_formatter import format_billing_insights
                    insights = format_billing_insights(billing_data, user_input, language)
                    if insights:
                        context_parts.append(insights)
                context = "\n\n".join(context_parts)
                from orchestration.llm_formatter import format_with_llm
                voice_reply = format_with_llm(context, user_input, language, is_voice=True)
                if voice_reply and voice_reply != context:
                    reply = voice_reply
                else:
                    reply = _strip_markdown_tables(reply)
            else:
                table_block = "\n\n".join(tool_tables)
                has_billing = any("(USD)" in t for t in tool_tables)
                if has_billing:
                    billing_data = _extract_billing_data_from_tools(messages)
                    from orchestration.llm_formatter import format_billing_insights
                    insights = format_billing_insights(billing_data, user_input, language)
                    table_with_insights = table_block + "\n\n" + insights if insights else table_block
                    if reply and len(reply) > 30:
                        reply = _replace_llm_table(reply, table_with_insights)
                    else:
                        reply = table_with_insights
                else:
                    if reply and len(reply) > 30:
                        reply = _replace_llm_table(reply, table_block)
                    else:
                        reply = table_block

        if is_voice and reply:
            reply = _strip_markdown_tables(reply)

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
            "reply": reply if reply else "No response generated.",
            "raw_messages": _serialize_messages(messages) if messages else [],
            "latency_ms": elapsed_ms,
            "tool_calls": tool_call_count,
            "path": "llm",
        }
    finally:
        current_chat_language.reset(lang_token)
        is_voice_mode.reset(voice_token)
