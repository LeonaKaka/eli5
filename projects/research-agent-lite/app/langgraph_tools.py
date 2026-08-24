from __future__ import annotations

from langchain.messages import AIMessage, HumanMessage, ToolMessage
from langchain.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition


@tool
def search_papers(query: str) -> str:
    """Return a deterministic teaching result for a paper-search query."""
    normalized = " ".join(query.strip().split())
    return f"paper:depinning-baseline | query={normalized}"


TOOLS = [search_papers]


def deterministic_model_node(state: MessagesState) -> dict[str, list[AIMessage]]:
    """Model-free teaching node that still emits real LangChain tool-call messages.

    A real chat model would decide whether to emit ``tool_calls``. Here we make
    that decision deterministic so ToolNode / ToolMessage / routing can be
    exercised in tests without a provider or API key.
    """

    messages = state["messages"]
    if not messages:
        return {"messages": [AIMessage(content="No user message provided.")]}

    last = messages[-1]
    if isinstance(last, HumanMessage):
        query = str(last.content)
        return {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": search_papers.name,
                            "args": {"query": query},
                            "id": "call-search-papers-1",
                            "type": "tool_call",
                        }
                    ],
                )
            ]
        }

    if isinstance(last, ToolMessage):
        return {
            "messages": [
                AIMessage(content=f"Grounded answer from tool result: {last.content}")
            ]
        }

    return {"messages": [AIMessage(content="Done.")]}


def build_tool_loop_graph():
    """Build the canonical model -> ToolNode -> model loop with real LangGraph APIs."""

    builder = StateGraph(MessagesState)
    builder.add_node("model", deterministic_model_node)
    builder.add_node("tools", ToolNode(TOOLS))
    builder.add_edge(START, "model")
    builder.add_conditional_edges("model", tools_condition)
    builder.add_edge("tools", "model")
    return builder.compile()


def run_tool_loop(query: str):
    graph = build_tool_loop_graph()
    return graph.invoke({"messages": [HumanMessage(content=query)]})
