from langchain_core.messages import SystemMessage, AIMessage, ToolMessage
from langchain.chat_models import init_chat_model

from models.state import AgentState
from agents.prompts import SYSTEM_PROMPT
from tools.registry import get_all_tools
from config.logging import get_logger
from config.settings import get_settings

logger = get_logger("agents.nodes")

_settings = get_settings()


def _get_llm_with_tools():
    llm = init_chat_model(
        model=_settings.llm_model,
        model_provider="openai",
        openai_api_base=_settings.open_api_base,
        openai_api_key=_settings.maas_api_key,
    )
    tools = get_all_tools()
    return llm.bind_tools(tools), tools


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
            "tool_names": [t.name for t in tools],
        }},
    )

    message = llm_with_tools.invoke(messages_with_system)

    has_tool_calls = hasattr(message, "tool_calls") and bool(message.tool_calls)
    logger.info(
        "Chatbot node response",
        extra={"structured_extra": {
            "has_tool_calls": has_tool_calls,
            "tool_calls": [{"name": tc["name"], "args": str(tc["args"])[:200]} for tc in message.tool_calls] if has_tool_calls else [],
            "content_preview": str(message.content)[:300] if not has_tool_calls else "TOOL_CALL",
        }},
    )

    return {"messages": [message]}
