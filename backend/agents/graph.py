from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

from models.state import AgentState
from agents.nodes import chatbot_node
from tools.registry import ToolRegistry
from config.logging import get_logger
from config.settings import get_settings

logger = get_logger("agents.graph")

_checkpointer = MemorySaver()


def _route_after_chatbot(state: AgentState) -> str:
    messages = state.get("messages", [])
    if not messages:
        return END

    last_message = messages[-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    return END


def build_graph(use_memory: bool = True) -> StateGraph:
    registry = ToolRegistry.get()
    tools = registry.get_all_tools()

    graph_builder = StateGraph(AgentState)

    graph_builder.add_node("chatbot", chatbot_node)

    tool_node = ToolNode(tools)
    graph_builder.add_node("tools", tool_node)

    graph_builder.add_conditional_edges("chatbot", _route_after_chatbot)

    graph_builder.add_edge("tools", "chatbot")
    graph_builder.add_edge(START, "chatbot")

    settings = get_settings()
    compiled = graph_builder.compile(
        checkpointer=_checkpointer if use_memory else None,
    )

    logger.info(
        "LangGraph compiled: %d tools, max_iterations=%d, memory=%s",
        len(tools), settings.max_graph_iterations, use_memory,
    )

    return compiled


def get_default_config(thread_id: str = "1") -> dict:
    return {"configurable": {"thread_id": thread_id}}
