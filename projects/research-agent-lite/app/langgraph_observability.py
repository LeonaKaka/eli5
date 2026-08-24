from __future__ import annotations

import operator
from typing import Annotated, Any
from typing_extensions import NotRequired, TypedDict

from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
from langchain.messages import AIMessage
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime


class TrackingAgentState(AgentState):
    model_call_count: NotRequired[int]
    blocked_by_budget: NotRequired[bool]


class CallBudgetMiddleware(AgentMiddleware[TrackingAgentState]):
    """Small real AgentMiddleware used to teach cross-cutting control.

    It does not call a model by itself. The hooks can be installed on create_agent;
    tests can also exercise the hook contract directly without a provider key.
    """

    state_schema = TrackingAgentState

    def __init__(self, *, max_model_calls: int = 3) -> None:
        super().__init__()
        if max_model_calls < 1:
            raise ValueError("max_model_calls must be >= 1")
        self.max_model_calls = max_model_calls

    @hook_config(can_jump_to=["end"])
    def before_model(
        self,
        state: TrackingAgentState,
        runtime: Runtime,
    ) -> dict[str, Any] | None:
        count = int(state.get("model_call_count", 0))
        if count < self.max_model_calls:
            return None
        return {
            "messages": [AIMessage(content="Model-call budget exhausted.")],
            "blocked_by_budget": True,
            "jump_to": "end",
        }

    def after_model(
        self,
        state: TrackingAgentState,
        runtime: Runtime,
    ) -> dict[str, Any] | None:
        return {
            "model_call_count": int(state.get("model_call_count", 0)) + 1,
            "blocked_by_budget": False,
        }


class StreamDemoState(TypedDict, total=False):
    objective: str
    evidence: Annotated[list[str], operator.add]
    answer: str


def build_streaming_graph():
    """Provider-free graph that emits real LangGraph state + custom stream events."""

    def retrieve(state: StreamDemoState) -> dict[str, list[str]]:
        writer = get_stream_writer()
        writer({"phase": "retrieve", "progress": 35, "objective": state["objective"]})
        return {"evidence": [f"evidence:{state['objective']}"]}

    def synthesize(state: StreamDemoState) -> dict[str, str]:
        writer = get_stream_writer()
        writer({"phase": "synthesize", "progress": 85, "evidence_count": len(state["evidence"])})
        return {"answer": f"answer from {len(state['evidence'])} evidence item(s)"}

    builder = StateGraph(StreamDemoState)
    builder.add_node("retrieve", retrieve)
    builder.add_node("synthesize", synthesize)
    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "synthesize")
    builder.add_edge("synthesize", END)
    return builder.compile()


def collect_stream_trace(objective: str) -> list[dict[str, Any]]:
    """Collect the v2 stream envelope for deterministic tests and UI examples."""

    graph = build_streaming_graph()
    parts: list[dict[str, Any]] = []
    for part in graph.stream(
        {"objective": objective, "evidence": [], "answer": ""},
        stream_mode=["updates", "values", "custom"],
        version="v2",
    ):
        parts.append(
            {
                "type": part["type"],
                "ns": tuple(part["ns"]),
                "data": part["data"],
            }
        )
    return parts
