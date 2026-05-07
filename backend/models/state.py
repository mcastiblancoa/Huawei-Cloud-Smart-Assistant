from typing import Annotated, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    intent: Optional[str]
    service: Optional[str]
    operation: Optional[str]
    params: Optional[dict]
    requires_confirmation: Optional[bool]
    confirmed: Optional[bool]
    execution_result: Optional[str]
    error: Optional[str]
