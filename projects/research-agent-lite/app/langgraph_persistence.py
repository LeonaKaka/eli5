from __future__ import annotations

import operator
from typing import Annotated
from typing_extensions import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph


class PersistenceState(TypedDict):
    objective: str
    stage: str
    events: Annotated[list[str], operator.add]


def normalize_objective(state: PersistenceState) -> dict[str, object]:
    return {
        "objective": " ".join(state["objective"].strip().split()),
        "stage": "normalized",
        "events": ["normalize"],
    }


def complete_run(state: PersistenceState) -> dict[str, object]:
    return {
        "stage": "completed",
        "events": [f"complete:{state['objective']}"],
    }


def build_persistent_graph(*, checkpointer: InMemorySaver | None = None):
    """Compile a deterministic graph with a real LangGraph checkpointer.

    `InMemorySaver` is intentionally used for teaching/tests. It demonstrates
    thread/checkpoint semantics but is not durable across process restarts.
    Production deployments should use a durable checkpointer integration.
    """

    saver = checkpointer or InMemorySaver()
    builder = StateGraph(PersistenceState)
    builder.add_node("normalize", normalize_objective)
    builder.add_node("complete", complete_run)
    builder.add_edge(START, "normalize")
    builder.add_edge("normalize", "complete")
    builder.add_edge("complete", END)
    return builder.compile(checkpointer=saver)


def thread_config(thread_id: str, *, checkpoint_id: str | None = None) -> dict[str, object]:
    if not thread_id.strip():
        raise ValueError("thread_id is required")
    configurable: dict[str, str] = {"thread_id": thread_id}
    if checkpoint_id is not None:
        configurable["checkpoint_id"] = checkpoint_id
    return {"configurable": configurable}
