from __future__ import annotations

import operator
from dataclasses import dataclass
from typing import Annotated
from typing_extensions import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from .agent_control import RunStatus
from .production import JobKind, ProductionControlPlane, RunJob, RunRecord


class ProductionGraphState(TypedDict, total=False):
    objective: str
    approval_required: bool
    events: Annotated[list[str], operator.add]
    result: str


def build_production_graph(*, checkpointer=None):
    """Provider-free graph used to demonstrate product-control integration.

    The graph owns thread/checkpoint/interrupt semantics. It deliberately does
    not own tenant authorization, queue claims, worker revisions or cancellation.
    """

    cp = checkpointer or InMemorySaver()

    def route(state: ProductionGraphState) -> Command:
        needs_approval = bool(state.get("approval_required"))
        return Command(
            update={"events": ["route:approval" if needs_approval else "route:execute"]},
            goto="approval" if needs_approval else "execute",
        )

    def approval(state: ProductionGraphState) -> Command:
        approved = interrupt(
            {
                "kind": "approval",
                "objective": state["objective"],
                "question": "Approve this exact action?",
            }
        )
        if not approved:
            return Command(update={"events": ["approval:rejected"]}, goto=END)
        return Command(update={"events": ["approval:approved"]}, goto="execute")

    def execute(state: ProductionGraphState) -> dict[str, object]:
        return {
            "events": ["execute"],
            "result": f"completed:{state['objective']}",
        }

    builder = StateGraph(ProductionGraphState)
    builder.add_node("route", route)
    builder.add_node("approval", approval)
    builder.add_node("execute", execute)
    builder.add_edge(START, "route")
    builder.add_edge("execute", END)
    return builder.compile(checkpointer=cp)


@dataclass(frozen=True)
class GraphRunOutcome:
    run: RunRecord
    thread_id: str
    interrupted: bool
    graph_result: dict | None = None


class ProductionGraphBridge:
    """Bridge LangGraph execution into the existing v4.0 product control plane.

    LangGraph handles graph checkpoints and interrupts. ProductionControlPlane
    remains authoritative for tenant scope, queue delivery, optimistic worker
    revisions, cancellation and whether an approval may enqueue a resume.
    """

    def __init__(self, *, control: ProductionControlPlane | None = None) -> None:
        self.control = control or ProductionControlPlane()
        self.checkpointer = InMemorySaver()
        self.graph = build_production_graph(checkpointer=self.checkpointer)
        self._resume_values: dict[tuple[str, str], bool] = {}

    @staticmethod
    def thread_id_for(*, tenant_id: str, run_id: str) -> str:
        if not tenant_id or not run_id:
            raise ValueError("tenant_id and run_id are required")
        return f"tenant:{tenant_id}:run:{run_id}"

    def submit(
        self,
        *,
        run_id: str,
        tenant_id: str,
        objective: str,
        approval_required: bool = False,
    ) -> RunRecord:
        marker = "approval:" if approval_required else "direct:"
        return self.control.submit(
            run_id=run_id,
            tenant_id=tenant_id,
            objective=f"{marker}{objective}",
        )

    def execute_job(self, job: RunJob) -> GraphRunOutcome:
        claim = self.control.claim(job)
        if not claim.accepted:
            return GraphRunOutcome(
                run=claim.record,
                thread_id=self.thread_id_for(tenant_id=job.tenant_id, run_id=job.run_id),
                interrupted=False,
                graph_result=None,
            )

        record = claim.record
        thread_id = self.thread_id_for(tenant_id=record.tenant_id, run_id=record.id)
        config = {"configurable": {"thread_id": thread_id}}

        if job.kind is JobKind.START:
            approval_required = record.objective.startswith("approval:")
            objective = record.objective.split(":", 1)[1]
            result = self.graph.invoke(
                {
                    "objective": objective,
                    "approval_required": approval_required,
                    "events": [],
                    "result": "",
                },
                config=config,
            )
        else:
            key = (record.tenant_id, record.id)
            if key not in self._resume_values:
                raise RuntimeError("resume job has no authorized application resume value")
            value = self._resume_values.pop(key)
            result = self.graph.invoke(Command(resume=value), config=config)

        if "__interrupt__" in result:
            snapshot = self.graph.get_state(config)
            checkpoint_id = snapshot.config["configurable"]["checkpoint_id"]
            approval_request_id = f"approval:{record.id}:r{record.revision}"
            paused = self.control.pause_for_approval(
                record.id,
                tenant_id=record.tenant_id,
                expected_revision=record.revision,
                approval_request_id=approval_request_id,
                checkpoint_id=checkpoint_id,
            )
            return GraphRunOutcome(
                run=paused,
                thread_id=thread_id,
                interrupted=True,
                graph_result=result,
            )

        finished = self.control.finish(
            record.id,
            tenant_id=record.tenant_id,
            expected_revision=record.revision,
            trace_events=len(result.get("events", [])),
        )
        return GraphRunOutcome(
            run=finished,
            thread_id=thread_id,
            interrupted=False,
            graph_result=result,
        )

    def resolve_approval(
        self,
        run_id: str,
        *,
        tenant_id: str,
        approval_request_id: str,
        approved: bool,
        actor_authorized: bool,
    ) -> RunRecord:
        """Application-side authorization gates whether a graph interrupt may resume."""

        current = self.control.store.get(run_id, tenant_id=tenant_id)
        if current.status is not RunStatus.WAITING_APPROVAL:
            raise ValueError("run is not waiting for approval")
        if current.approval_request_id != approval_request_id:
            raise ValueError("approval request does not match paused run")
        if not actor_authorized:
            raise PermissionError("actor is not authorized to resolve this approval")

        if not approved:
            return self.control.request_cancel(run_id, tenant_id=tenant_id)

        self._resume_values[(tenant_id, run_id)] = True
        return self.control.enqueue_resume_after_approval(
            run_id,
            tenant_id=tenant_id,
            approval_request_id=approval_request_id,
        )

    def get_graph_state(self, run_id: str, *, tenant_id: str):
        """Tenant-check product state first, then inspect its graph thread."""

        self.control.store.get(run_id, tenant_id=tenant_id)
        config = {
            "configurable": {
                "thread_id": self.thread_id_for(tenant_id=tenant_id, run_id=run_id)
            }
        }
        return self.graph.get_state(config)
