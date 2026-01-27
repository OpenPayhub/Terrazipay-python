import os

from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

import webbrowser

from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from ...terrazip.utils import setup_logger
from .tools_example import TOOLS
from .state import PaymentAgentState
from .prompts import SYSTEM_PROMPT

import asyncio


class PaymentAgent:
    def __init__(
        self,
        env_path: str = "src/terrazip/ai/.env.ai",
        key_name: str = "DEEPSEEK_API_KEY",
        model_base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
    ):
        """
        Initializes the Payment Agent by loading environment variables,
        setting up the LLM, and compiling the state graph.
        """
        load_dotenv(dotenv_path=env_path)
        self.checkpointer = InMemorySaver()
        self.llm = self._init_llm(
            key_name=key_name, model_base_url=model_base_url, model=model
        )
        self.model_with_tools = self.llm.bind_tools(
            TOOLS
        )  # Ensure TOOLS is defined globally
        self.graph = self._build_graph()

    def _init_llm(self, key_name: str, model_base_url: str, model: str) -> ChatOpenAI:
        """Sets up the DeepSeek LLM configuration."""
        api_key = os.getenv(key_name)
        if not api_key:
            raise ValueError(f"{key_name} not found in .env file")

        return ChatOpenAI(
            base_url=model_base_url,
            api_key=api_key,
            model=model,
        )

    def _should_call_tool(self, state: PaymentAgentState):
        """Conditional logic to decide whether to call a tool or finish."""
        last_msg = state["messages"][-1]
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            return "tool"
        return "end"

    async def _llm_node(self, state: PaymentAgentState):
        """Processes the message history and generates a response."""
        response = await self.model_with_tools.ainvoke(state["messages"])
        return {
            "messages": [response]
        }  # LangGraph appends automatically if using Annotated messages

    def _open_browser_node(self, state: PaymentAgentState):
        """Action node to open a payment URL if it exists in the state."""
        if state.get("payment_url") and not state.get("browser_opened"):
            webbrowser.open(state["payment_url"])
            return {"browser_opened": True}
        return {}

    def _build_graph(self):
        """Defines the workflow structure and compiles it."""
        workflow = StateGraph(PaymentAgentState)

        # Add Nodes
        workflow.add_node("llm", self._llm_node)
        workflow.add_node("tools", ToolNode(TOOLS))
        workflow.add_node("open_browser", self._open_browser_node)

        # Set Entry and Edges
        workflow.set_entry_point("llm")

        workflow.add_conditional_edges(
            "llm", self._should_call_tool, {"tool": "tools", "end": "open_browser"}
        )

        workflow.add_edge("tools", "llm")
        workflow.add_edge(
            "open_browser", END
        )  # Note: Ensure wait_for_payment logic is handled or added

        return workflow.compile(checkpointer=self.checkpointer)

    async def run_chat(self, thread_id: str = "default_thread"):
        """
        Starts an interactive CLI session for the agent.
        """
        config = {"configurable": {"thread_id": thread_id}}
        print("--- Payment Agent Started (Type 'quit' to exit) ---")

        while True:
            user_input = input("User: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                break

            input_data = {
                "messages": [
                    HumanMessage(content=user_input),
                    SystemMessage(content=SYSTEM_PROMPT),
                ]
            }
            async for event in self.graph.astream_events(
                input_data, config, version="v1"
            ):
                # Get the last message in the sequence
                if event["event"] == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if chunk.content:
                        print(chunk.content, end="", flush=True)

        print("\n")


if __name__ == "__main__":
    # To run this, ensure PaymentAgentState and TOOLS are defined in your scope
    agent = PaymentAgent()
    asyncio.run(agent.run_chat())
