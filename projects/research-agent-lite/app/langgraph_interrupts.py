from __future__ import annotations

import operator
from typing import Annotated, Literal
from typing_extensions import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class ApprovalState(TypedDict):
    action: str
    status: Literal["pending", "approved", "rejected"]
    events: Annotated[list[str], operator.add]


def build_approval_graph(*, execution_log: list[str] | None = None):
    """Pause before a side effect and execute it only after approval.

    The node containing ``interrupt()`` may restart from its beginning on
    resume. Therefore everything before the interrupt is deliberately pure.
    The observable side effect is placed in a downstream node after approval.
    """

    log = execution_log if execution_log is not None else []

    def approval_node(state: ApprovalState) -> Command[Literal["execute", "cancel"]]:
        approved = interrupt(
            {
                "question": "Approve this action?",
                "action": state["action"],
            }
        )
        route: Literal["execute", "cancel"] = "execute" if bool(approved) else "cancel"
        return Command(
            update={"events": [f"decision:{'approved' if approved else 'rejected'}"]},
            goto=route,
        )

    def execute_node(state: ApprovalState) -> dict[str, object]:
        log.append(state["action"])
        return {"status": "approved", "events": ["execute"]}

    def cancel_node(state: ApprovalState) -> dict[str, object]:
        return {"status": "rejected", "events": ["cancel"]}

    builder = StateGraph(ApprovalState)
    builder.add_node("approval", approval_node)
    builder.add_node("execute", execute_node)
    builder.add_node("cancel", cancel_node)
    builder.add_edge(START, "approval")
    builder.add_edge("execute", END)
    builder.add_edge("cancel", END)
    return builder.compile(checkpointer=InMemorySaver())


def build_unsafe_pre_interrupt_graph(*, execution_log: list[str]):
    """Deliberately unsafe demo: a side effect happens before interrupt().

    On resume LangGraph restarts the interrupted node from the beginning, so the
    pre-interrupt effect is observed twice during a normal pause/resume cycle.
    This module exists to make the replay-safety warning executable in tests.
    """

    def approval_node(state: ApprovalState) -> Command[Literal["done", "cancel"]]:
        execution_log.append(state["action"])
        approved = interrupt({"question": "Approve?", "action": state["action"]})
        return Command(goto="done" if approved else "cancel")

    def done_node(state: ApprovalState) -> dict[str, object]:
        return {"status": "approved", "events": ["done"]}

    def cancel_node(state: ApprovalState) -> dict[str, object]:
        return {"status": "rejected", "events": ["cancel"]}

    builder = StateGraph(ApprovalState)
    builder.add_node("approval", approval_node)
    builder.add_node("done", done_node)
    builder.add_node("cancel", cancel_node)
    builder.add_edge(START, "approval")
    builder.add_edge("done", END)
    builder.add_edge("cancel", END)
    return builder.compile(checkpointer=InMemorySaver())
