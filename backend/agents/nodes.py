import time

from langchain_core.messages import SystemMessage, AIMessage
from langchain.chat_models import init_chat_model

from models.state import AgentState
from agents.prompts import SYSTEM_PROMPT
from tools.registry import ToolRegistry
from config.logging import get_logger
from config.settings import get_settings

logger = get_logger("agents.nodes")

_settings = get_settings()

RATE_LIMIT_RETRIES = 6
RATE_LIMIT_BASE_DELAY = 3.0

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


def chatbot_node(state: AgentState) -> dict:
    llm_with_tools, tools = _get_llm_with_tools()
    system_msg = SystemMessage(content=SYSTEM_PROMPT)
    messages_with_system = [system_msg] + state["messages"]

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
            is_rate_limit = "RateLimit" in error_name or "429" in str(e) or "TooMany" in str(e)
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
