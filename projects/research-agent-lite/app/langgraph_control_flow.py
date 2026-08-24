from __future__ import annotations

import operator
from typing import Annotated, Literal
from typing_extensions import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Send


class CommandState(TypedDict):
    objective: str
    route: Literal["research", "direct"] | None
    events: Annotated[list[str], operator.add]
    answer: str | None


def decide_with_command(
    state: CommandState,
) -> Command[Literal["research", "direct"]]:
    objective = state["objective"].lower()
    route: Literal["research", "direct"] = (
        "research" if any(word in objective for word in ("paper", "research", "evidence")) else "direct"
    )
    return Command(
        update={"route": route, "events": [f"decide:{route}"]},
        goto=route,
    )


def research_node(state: CommandState) -> dict[str, object]:
    return {
        "events": ["research"],
        "answer": f"researched:{state['objective']}",
    }


def direct_node(state: CommandState) -> dict[str, object]:
    return {
        "events": ["direct"],
        "answer": f"direct:{state['objective']}",
    }


def build_command_graph():
    """Use Command when one node must update state and choose the next hop together."""

    builder = StateGraph(CommandState)
    builder.add_node("decide", decide_with_command)
    builder.add_node("research", research_node)
    builder.add_node("direct", direct_node)
    builder.add_edge(START, "decide")
    builder.add_edge("research", END)
    builder.add_edge("direct", END)
    return builder.compile()


class RetrievalBatchState(TypedDict):
    queries: list[str]
    evidence: Annotated[list[str], operator.add]
    summary: str


def prepare_batch(state: RetrievalBatchState) -> dict[str, object]:
    # Keeping a real node before Send makes the fan-out point visible in the graph.
    return {}


def fan_out_queries(state: RetrievalBatchState) -> list[Send]:
    return [Send("retrieve_one", {"query": query}) for query in state["queries"]]


def retrieve_one(state: dict[str, str]) -> dict[str, list[str]]:
    query = " ".join(state["query"].strip().split())
    return {"evidence": [f"evidence:{query}"]}


def summarize_batch(state: RetrievalBatchState) -> dict[str, str]:
    ordered = sorted(state["evidence"])
    return {"summary": f"{len(ordered)} evidence item(s): " + " | ".join(ordered)}


def build_send_map_reduce_graph():
    """Dynamic fan-out with Send, reducer-based fan-in, then one summarize node."""

    builder = StateGraph(RetrievalBatchState)
    builder.add_node("prepare", prepare_batch)
    builder.add_node("retrieve_one", retrieve_one)
    builder.add_node("summarize", summarize_batch)
    builder.add_edge(START, "prepare")
    builder.add_conditional_edges("prepare", fan_out_queries, ["retrieve_one"])
    builder.add_edge("retrieve_one", "summarize")
    builder.add_edge("summarize", END)
    return builder.compile()
