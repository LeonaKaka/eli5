from __future__ import annotations

from operator import add
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class BridgeState(TypedDict):
    objective: str
    events: Annotated[list[str], add]
    step_count: int


def normalize_objective(state: BridgeState) -> dict[str, object]:
    """Small deterministic node used to map the old hand-written loop into a graph."""
    objective = state["objective"].strip()
    return {
        "objective": objective,
        "events": ["normalize_objective"],
        "step_count": state.get("step_count", 0) + 1,
    }


def build_bridge_graph():
    """v4.1: the smallest real LangGraph used by the course.

    The graph is intentionally deterministic and model-free. Its purpose is to
    prove the execution contract: typed shared state -> node partial updates ->
    edges -> compiled runnable graph.
    """
    builder = StateGraph(BridgeState)
    builder.add_node("normalize", normalize_objective)
    builder.add_edge(START, "normalize")
    builder.add_edge("normalize", END)
    return builder.compile()


class ResearchGraphState(TypedDict):
    objective: str
    mode: Literal["auto", "research", "direct"]
    route: Literal["research", "direct"] | None
    evidence: Annotated[list[str], add]
    events: Annotated[list[str], add]
    step_count: int
    answer: str | None


def classify_request(state: ResearchGraphState) -> dict[str, object]:
    """Deterministic teaching router; a real app can replace this node with a model."""
    requested = state.get("mode", "auto")
    if requested == "research":
        route: Literal["research", "direct"] = "research"
    elif requested == "direct":
        route = "direct"
    else:
        route = "research" if "paper" in state["objective"].lower() else "direct"
    return {
        "route": route,
        "events": [f"classify:{route}"],
        "step_count": state.get("step_count", 0) + 1,
    }


def route_after_classify(state: ResearchGraphState) -> Literal["research", "direct"]:
    route = state.get("route")
    if route not in {"research", "direct"}:
        raise ValueError("classify_request must set a valid route")
    return route


def research_node(state: ResearchGraphState) -> dict[str, object]:
    return {
        "evidence": [f"evidence:{state['objective']}"],
        "events": ["research"],
        "step_count": state.get("step_count", 0) + 1,
    }


def direct_node(state: ResearchGraphState) -> dict[str, object]:
    return {
        "events": ["direct"],
        "step_count": state.get("step_count", 0) + 1,
    }


def synthesize_node(state: ResearchGraphState) -> dict[str, object]:
    if state.get("route") == "research":
        evidence_count = len(state.get("evidence", []))
        answer = f"research answer with {evidence_count} evidence item(s)"
    else:
        answer = "direct answer"
    return {
        "answer": answer,
        "events": ["synthesize"],
        "step_count": state.get("step_count", 0) + 1,
    }


def build_research_state_graph():
    """v4.2: typed state + reducers + fixed/conditional edges."""
    builder = StateGraph(ResearchGraphState)
    builder.add_node("classify", classify_request)
    builder.add_node("research", research_node)
    builder.add_node("direct", direct_node)
    builder.add_node("synthesize", synthesize_node)

    builder.add_edge(START, "classify")
    builder.add_conditional_edges(
        "classify",
        route_after_classify,
        {
            "research": "research",
            "direct": "direct",
        },
    )
    builder.add_edge("research", "synthesize")
    builder.add_edge("direct", "synthesize")
    builder.add_edge("synthesize", END)
    return builder.compile()


def initial_research_state(
    objective: str,
    *,
    mode: Literal["auto", "research", "direct"] = "auto",
) -> ResearchGraphState:
    return {
        "objective": objective,
        "mode": mode,
        "route": None,
        "evidence": [],
        "events": [],
        "step_count": 0,
        "answer": None,
    }
