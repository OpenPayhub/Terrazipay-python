from typing import TypedDict, List, Optional, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages

class PaymentAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    payment_url: Optional[str]
    browser_opened: bool
    order_id: str

