from config.logging import get_logger

logger = get_logger("memory.checkpointer")

logger.warning(
    "memory/checkpointer.py is deprecated. The LangGraph graph in agents/graph.py "
    "creates its own MemorySaver instance. This module is unused."
)


def get_checkpointer():
    raise NotImplementedError(
        "Use the checkpointer from agents/graph.py instead."
    )
