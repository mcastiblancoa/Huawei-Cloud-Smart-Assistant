import time

from langchain_core.messages import SystemMessage, AIMessage, ToolMessage
from langchain.chat_models import init_chat_model

from models.state import AgentState
from agents.prompts import SYSTEM_PROMPT
from orchestration.lang_context import current_chat_language
from tools.registry import ToolRegistry
from config.logging import get_logger
from config.settings import get_settings

logger = get_logger("agents.nodes")

_settings = get_settings()

RATE_LIMIT_RETRIES = 6
RATE_LIMIT_BASE_DELAY = 3.0
TOOL_RESULT_MAX_CHARS = 3000

_llm_with_tools_cache = None


def _get_llm_with_tools():
    global _llm_with_tools_cache
    if _llm_with_tools_cache is not None:
        return _llm_with_tools_cache

    llm = init_chat_model(
        model=_settings.llm_model,
        model_provider="openai",
        openai_api_base=_settings.open_api_base,
        openai_api_key=_settings.maas_api_key,
        max_retries=1,
    )
    registry = ToolRegistry.get()
    tools = registry.get_all_tools()
    bound = llm.bind_tools(tools)
    _llm_with_tools_cache = (bound, tools)
    return _llm_with_tools_cache


def _prune_messages(messages: list, max_tool_chars: int = TOOL_RESULT_MAX_CHARS) -> list:
    """Truncate long tool results and prune very old messages to keep context manageable."""
    pruned = []
    total_chars = 0
    for msg in messages:
        if isinstance(msg, ToolMessage):
            content = getattr(msg, "content", "")
            if isinstance(content, str) and len(content) > max_tool_chars:
                truncated = content[:max_tool_chars] + f"\n...[truncated, {len(content)} chars total]"
                msg = ToolMessage(
                    content=truncated,
                    tool_call_id=msg.tool_call_id,
                    name=getattr(msg, "name", None),
                )
                total_chars += len(truncated)
            else:
                total_chars += len(content) if isinstance(content, str) else 0
        else:
            content = getattr(msg, "content", "")
            total_chars += len(content) if isinstance(content, str) else 0
        pruned.append(msg)
    return pruned


def chatbot_node(state: AgentState) -> dict:
    llm_with_tools, tools = _get_llm_with_tools()
    lang = current_chat_language.get()
    lang_block = ""
    if lang == "es":
        lang_block = "\n\n[IDIOMA: el usuario interactúa en español. Todas las respuestas deben ser en español.]"
    elif lang == "en":
        lang_block = "\n\n[LANGUAGE: the user expects English replies.]"
    system_msg = SystemMessage(content=SYSTEM_PROMPT + lang_block)

    pruned = _prune_messages(state["messages"])
    messages_with_system = [system_msg] + pruned

    logger.info(
        "Chatbot node invoked",
        extra={"structured_extra": {
            "message_count": len(state["messages"]),
            "model": _settings.llm_model,
            "tools_count": len(tools),
        }},
    )

    message = None
    for attempt in range(RATE_LIMIT_RETRIES + 1):
        try:
            message = llm_with_tools.invoke(messages_with_system)
            break
        except Exception as e:
            error_name = type(e).__name__
            error_str = str(e)
            is_rate_limit = "RateLimit" in error_name or "429" in error_str or "TooMany" in error_str
            is_content_filter = "403" in error_str or "PermissionDenied" in error_name or "81011" in error_str or "sensitive" in error_str.lower()
            if is_content_filter:
                logger.warning("ModelArts content filter triggered (attempt %d), retrying with safe prompt", attempt)
                safe_suffix = "\n\n[CONTENT SAFETY: Do NOT include any UUIDs, IDs, IP addresses, credentials, or sensitive data in your response. Use only resource names and regions.]"
                safe_system = SystemMessage(content=SYSTEM_PROMPT + lang_block + safe_suffix)
                try:
                    message = llm_with_tools.invoke([safe_system] + pruned)
                    break
                except Exception:
                    return {"messages": [AIMessage(content="No pude completar la respuesta debido a restricciones de contenido. Por favor, reformula tu pregunta.")]}
            if is_rate_limit and attempt < RATE_LIMIT_RETRIES:
                delay = RATE_LIMIT_BASE_DELAY * (2 ** attempt)
                logger.warning("Rate limit hit, retrying in %.1fs", delay)
                time.sleep(delay)
                continue
            if is_rate_limit:
                logger.error("Rate limit exhausted after %d retries", RATE_LIMIT_RETRIES)
                return {"messages": [AIMessage(content="The AI service is temporarily busy. Please try again in a moment.")]}
            raise

    has_tool_calls = hasattr(message, "tool_calls") and bool(message.tool_calls)
    logger.info(
        "Chatbot node response",
        extra={"structured_extra": {
            "has_tool_calls": has_tool_calls,
            "tool_calls": [{"name": tc["name"]} for tc in message.tool_calls] if has_tool_calls else [],
        }},
    )

    return {"messages": [message]}
