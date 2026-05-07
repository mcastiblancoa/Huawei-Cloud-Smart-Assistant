from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

from models.state import AgentState
from agents.nodes import chatbot_node
from tools.registry import get_all_tools
from config.logging import get_logger

logger = get_logger("agents.graph")

_checkpointer = MemorySaver()

MAX_ITERATIONS = 50


def build_graph(use_memory: bool = True, max_iterations: int = MAX_ITERATIONS) -> StateGraph:
    tools = get_all_tools()

    graph_builder = StateGraph(AgentState)

    graph_builder.add_node("chatbot", chatbot_node)

    tool_node = ToolNode(tools)
    graph_builder.add_node("tools", tool_node)

    graph_builder.add_conditional_edges("chatbot", tools_condition)

    graph_builder.add_edge("tools", "chatbot")
    graph_builder.add_edge(START, "chatbot")

    compiled = graph_builder.compile(
        checkpointer=_checkpointer if use_memory else None,
    )

    logger.info(
        "LangGraph compiled with %d tools, max_iterations=%d, memory=%s",
        len(tools), max_iterations, use_memory,
    )

    return compiled


def get_default_config(thread_id: str = "1") -> dict:
    return {"configurable": {"thread_id": thread_id}}
