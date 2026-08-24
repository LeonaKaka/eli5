from __future__ import annotations

import operator
from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command


def _replace(_old: str, new: str) -> str:
    return new


class SharedParentState(TypedDict, total=False):
    objective: str
    evidence: str
    result: str


class SharedRetrievalState(TypedDict, total=False):
    objective: str
    evidence: str
    scratch: str


def build_shared_state_subgraph():
    """A subgraph added directly as a parent node because state keys overlap."""

    def analyze(state: SharedRetrievalState) -> dict[str, str]:
        return {"scratch": f"terms:{state['objective']}"}

    def retrieve(state: SharedRetrievalState) -> dict[str, str]:
        return {"evidence": f"evidence-for:{state['objective']} | {state['scratch']}"}

    child_builder = StateGraph(SharedRetrievalState)
    child_builder.add_node("analyze", analyze)
    child_builder.add_node("retrieve", retrieve)
    child_builder.add_edge(START, "analyze")
    child_builder.add_edge("analyze", "retrieve")
    child_builder.add_edge("retrieve", END)
    child = child_builder.compile()

    def synthesize(state: SharedParentState) -> dict[str, str]:
        return {"result": f"answer from {state['evidence']}"}

    parent_builder = StateGraph(SharedParentState)
    parent_builder.add_node("retrieval_subgraph", child)
    parent_builder.add_node("synthesize", synthesize)
    parent_builder.add_edge(START, "retrieval_subgraph")
    parent_builder.add_edge("retrieval_subgraph", "synthesize")
    parent_builder.add_edge("synthesize", END)
    return parent_builder.compile()


class PrivateWriterState(TypedDict, total=False):
    question: str
    notes: str
    draft: str


class PrivateParentState(TypedDict, total=False):
    objective: str
    specialist_result: str


def build_private_state_subgraph_parent():
    """Call a subgraph inside a wrapper node when parent/child schemas differ."""

    def plan(state: PrivateWriterState) -> dict[str, str]:
        return {"notes": f"private-plan:{state['question']}"}

    def write(state: PrivateWriterState) -> dict[str, str]:
        return {"draft": f"specialist-draft:{state['question']} | {state['notes']}"}

    child_builder = StateGraph(PrivateWriterState)
    child_builder.add_node("plan", plan)
    child_builder.add_node("write", write)
    child_builder.add_edge(START, "plan")
    child_builder.add_edge("plan", "write")
    child_builder.add_edge("write", END)
    child = child_builder.compile()

    def call_writer(state: PrivateParentState) -> dict[str, str]:
        child_result = child.invoke({"question": state["objective"]})
        return {"specialist_result": child_result["draft"]}

    parent_builder = StateGraph(PrivateParentState)
    parent_builder.add_node("writer_wrapper", call_writer)
    parent_builder.add_edge(START, "writer_wrapper")
    parent_builder.add_edge("writer_wrapper", END)
    return parent_builder.compile()


class TeamState(TypedDict, total=False):
    objective: str
    handoff_payload: Annotated[str, _replace]
    events: Annotated[list[str], operator.add]
    draft: str


class RetrieverAgentState(TypedDict, total=False):
    objective: str
    scratch: str
    handoff_payload: Annotated[str, _replace]
    events: Annotated[list[str], operator.add]


def build_parent_handoff_graph():
    """A deterministic subgraph -> parent handoff using Command.PARENT.

    The retriever keeps private scratch state, then sends only an explicit handoff
    payload and event back to the closest parent graph before routing to writer_agent.
    """

    def retrieve(state: RetrieverAgentState) -> dict[str, str]:
        return {"scratch": f"evidence:{state['objective']}"}

    def handoff(state: RetrieverAgentState) -> Command:
        return Command(
            update={
                "handoff_payload": state["scratch"],
                "events": ["handoff:retriever→writer"],
            },
            goto="writer_agent",
            graph=Command.PARENT,
        )

    retriever_builder = StateGraph(RetrieverAgentState)
    retriever_builder.add_node("retrieve", retrieve)
    retriever_builder.add_node("handoff", handoff)
    retriever_builder.add_edge(START, "retrieve")
    retriever_builder.add_edge("retrieve", "handoff")
    retriever_agent = retriever_builder.compile()

    def writer_agent(state: TeamState) -> dict[str, object]:
        return {
            "draft": f"writer-used:{state['handoff_payload']}",
            "events": ["writer:done"],
        }

    parent_builder = StateGraph(TeamState)
    parent_builder.add_node("retriever_agent", retriever_agent)
    parent_builder.add_node("writer_agent", writer_agent)
    parent_builder.add_edge(START, "retriever_agent")
    # No static edge out of retriever_agent: Command.PARENT owns that routing decision.
    parent_builder.add_edge("writer_agent", END)
    return parent_builder.compile()
