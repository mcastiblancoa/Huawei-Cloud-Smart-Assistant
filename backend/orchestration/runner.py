import time
import re
import json
from typing import Any

from config.settings import get_settings
from config.logging import get_logger
from orchestration.router import route_intent
from orchestration.formatter import format_response, _build_resource_context, _format_billing_natural, _format_resources_natural
from orchestration.llm_formatter import format_with_llm, format_billing_insights
from orchestration.lang_context import is_voice_mode
from tools.registry import ToolRegistry
from tools.common.table_formatter import format_billing_table_multi

logger = get_logger("orchestration.runner")

_GREETINGS_ES = set()
_GREETINGS_EN = set()
_SMALL_TALK = set()

def _count_table_rows(table_md: str) -> int:
    lines = table_md.strip().split("\n")
    count = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if re.match(r'^\|[-\s|:]+\|$', stripped):
            continue
        prev = lines[i - 1].strip() if i > 0 else ""
        if re.match(r'^\|[-\s|:]+\|$', prev):
            continue
        count += 1
    return count


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


_LAST_BILL_CYCLE: dict[str, str] = {}

_MONTH_MAP = {
    "enero": "01", "january": "01", "febrero": "02", "february": "02",
    "marzo": "03", "march": "03", "abril": "04", "april": "04",
    "mayo": "05", "may": "05", "junio": "06", "june": "06",
    "julio": "07", "july": "07", "agosto": "08", "august": "08",
    "septiembre": "09", "september": "09", "octubre": "10", "october": "10",
    "noviembre": "11", "november": "11", "diciembre": "12", "december": "12",
}


def _is_greeting(text: str) -> bool:
    lower = text.lower().strip().rstrip("!.").strip()
    lower = re.sub(r'á', 'a', lower)
    lower = re.sub(r'í', 'i', lower)
    lower = re.sub(r'ó', 'o', lower)
    if lower in _GREETINGS_ES or lower in _GREETINGS_EN or lower in _SMALL_TALK:
        return True
    for g in _GREETINGS_ES | _GREETINGS_EN:
        if lower.startswith(g) and len(lower) < 30:
            return True
    return False


def _greeting_response(text: str, language: str) -> str:
    lower = text.lower().strip()
    if lower.rstrip("!.") in _SMALL_TALK:
        if language == "es":
            return "¡De nada! Dime si necesitas algo más."
        return "You're welcome! Let me know if you need anything else."
    if language == "es":
        return "¡Hola! ¿En qué te puedo ayudar con Huawei Cloud?"
    return "Hi! How can I help you with Huawei Cloud?"


def _detect_multi_month_billing(text: str) -> list[str] | None:
    lower = text.lower()
    found_months = []
    for month_name, month_num in _MONTH_MAP.items():
        if month_name in lower:
            year_match = re.search(r'\b(20[2-9]\d)\b', text)
            year = year_match.group(1) if year_match else str(time.gmtime().tm_year)
            found_months.append(f"{year}-{month_num}")
    if len(found_months) >= 2:
        return found_months
    return None


def _detect_followup_billing(text: str, session_id: str) -> dict | None:
    lower = text.lower().strip()
    is_billing_followup = any(kw in lower for kw in ["y en", "y el", "and in", "and for", "también en", "also in"])
    if not is_billing_followup:
        return None

    last_cycle = _LAST_BILL_CYCLE.get(session_id)
    if not last_cycle:
        return None

    year = last_cycle[:4]

    for month_name, month_num in _MONTH_MAP.items():
        if month_name in lower:
            return {"tool": "get_monthly_costs", "params": {"bill_cycle": f"{year}-{month_num}"}, "response_type": "billing"}

    year_match = re.search(r'\b(20[2-9]\d)\b', text)
    if year_match:
        new_year = year_match.group(1)
        month = last_cycle[5:7]
        return {"tool": "get_monthly_costs", "params": {"bill_cycle": f"{new_year}-{month}"}, "response_type": "billing"}

    return None


def _execute_tool(registry: ToolRegistry, tool_name: str, params: dict) -> dict:
    tool = registry.get_tool(tool_name)
    if not tool:
        return {"ok": False, "error": f"Tool {tool_name} not found"}
    try:
        result = tool.invoke(params)
        return json.loads(result) if isinstance(result, str) else result
    except Exception as exc:
        logger.exception("Tool execution failed: %s", tool_name)
        return {"ok": False, "error": str(exc)}


def _table_to_voice_prose(table_md: str, data: Any, response_type: str, user_query: str, language: str) -> str:
    context = _build_resource_context(data, response_type) if data and isinstance(data, dict) else table_md
    if context and context != "Total: 0":
        voice_reply = format_with_llm(context, user_query, language, is_voice=True)
        if voice_reply and voice_reply != context:
            return voice_reply
    if data and isinstance(data, dict):
        if response_type == "billing":
            natural = _format_billing_natural(data, language)
        else:
            natural = _format_resources_natural(data, response_type, language)
        if natural:
            return natural
    return table_md


def run_fast_path(message: str, language: str, session_id: str = "default") -> str | None:
    if _is_greeting(message):
        return _greeting_response(message, language)

    registry = ToolRegistry.get()

    multi_months = _detect_multi_month_billing(message)
    if multi_months:
        results = []
        for cycle in multi_months:
            payload = _execute_tool(registry, "get_monthly_costs", {"bill_cycle": cycle})
            if payload.get("ok") and payload.get("data"):
                results.append(payload["data"])
            else:
                results.append({"month": cycle, "total": 0, "currency": "USD", "services": [], "error": payload.get("error")})

        _LAST_BILL_CYCLE[session_id] = multi_months[-1]

        table_md = format_billing_table_multi(results)
        if table_md:
            insights = format_billing_insights(results, message, language)
            if is_voice_mode.get():
                context = table_md
                if insights:
                    context += "\n\n" + insights
                voice_reply = format_with_llm(context, message, language, is_voice=True)
                if voice_reply and voice_reply != context:
                    return voice_reply
                parts = []
                for r in results:
                    parts.append(_format_billing_natural(r, language))
                return "\n\n".join(parts)
            if insights:
                return table_md + "\n\n" + insights
            return table_md

        context_parts = []
        for r in results:
            ctx = _build_resource_context(r, "billing")
            context_parts.append(ctx)
        context = "\n\n---\n\n".join(context_parts)

        llm_response = format_with_llm(context, message, language)
        if llm_response != context:
            return llm_response

        parts = []
        for r in results:
            parts.append(_format_billing_natural(r, language))
        return "\n\n".join(parts)

    followup = _detect_followup_billing(message, session_id)
    if followup:
        payload = _execute_tool(registry, followup["tool"], followup["params"])
        data = payload.get("data")
        table_md = payload.get("_table", "")

        if followup["params"].get("bill_cycle"):
            _LAST_BILL_CYCLE[session_id] = followup["params"]["bill_cycle"]

        if table_md:
            insights = format_billing_insights([data] if data else [], message, language)
            if is_voice_mode.get():
                context = table_md
                if insights:
                    context += "\n\n" + insights
                voice_reply = format_with_llm(context, message, language, is_voice=True)
                if voice_reply and voice_reply != context:
                    return voice_reply
                if data:
                    natural = _format_billing_natural(data, language)
                    if natural:
                        return natural
                return context
            if insights:
                return table_md + "\n\n" + insights
            return table_md

        context = _build_resource_context(data, followup["response_type"]) if data else "No data"
        llm_response = format_with_llm(context, message, language)
        if llm_response != context:
            return llm_response

        if data:
            natural = _format_billing_natural(data, language)
            if natural:
                return natural
        return context

    decision = route_intent(message)
    if decision is None:
        return None

    payload = _execute_tool(registry, decision.tool, decision.params)
    if not payload.get("ok") and not payload.get("message"):
        error = payload.get("error", "Unknown error")
        return f"Error: {error[:200]}"

    data = payload.get("data")
    msg = payload.get("message", "")
    table_md = payload.get("_table", "")

    if decision.response_type == "billing" and decision.params.get("bill_cycle"):
        _LAST_BILL_CYCLE[session_id] = decision.params["bill_cycle"]

    if data and isinstance(data, dict):
        if table_md:
            if is_voice_mode.get():
                billing_data = [data] if decision.response_type == "billing" else []
                insights = format_billing_insights(billing_data, message, language) if billing_data else ""
                context = table_md
                if insights:
                    context += "\n\n" + insights
                return _table_to_voice_prose(context, data, decision.response_type, message, language)
            billing_data = [data] if decision.response_type == "billing" else []
            insights = format_billing_insights(billing_data, message, language) if billing_data else ""
            table_with_extra = table_md + "\n\n" + insights if insights else table_md
            context = _build_resource_context(data, decision.response_type)
            if context and context != "Total: 0":
                llm_response = format_with_llm(context, message, language)
                if llm_response and llm_response != context and len(llm_response) > 30:
                    return _replace_llm_table(llm_response, table_with_extra)
            return table_with_extra
        context = _build_resource_context(data, decision.response_type)
        if context and context != "Total: 0":
            llm_response = format_with_llm(context, message, language)
            if llm_response != context:
                return llm_response
            natural = _format_resources_natural(data, decision.response_type, language) if decision.response_type != "billing" else _format_billing_natural(data, language)
            if natural:
                return natural

    if msg:
        return msg

    quick = format_response(decision.response_type, payload, language)
    return quick
