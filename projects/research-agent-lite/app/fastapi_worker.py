from __future__ import annotations

from dataclasses import dataclass

import anyio

from .agent_control import RunStatus
from .fastapi_streaming import InMemoryRunEventStore, RunEventType
from .langgraph_production import GraphRunOutcome, ProductionGraphBridge
from .production import RunJob


@dataclass(frozen=True)
class WorkerTickResult:
    job: RunJob | None
    outcome: GraphRunOutcome | None

    @property
    def had_job(self) -> bool:
        return self.job is not None


async def run_one_worker_tick(
    bridge: ProductionGraphBridge,
    *,
    events: InMemoryRunEventStore | None = None,
) -> WorkerTickResult:
    """Pop and execute one durable job outside the HTTP request lifecycle.

    The current graph bridge exposes a synchronous execution API. A worker that
    itself runs an async loop can isolate that blocking adapter with AnyIO's
    thread offload. This is not a reason to run the Agent inside a FastAPI request.
    """

    job = bridge.control.queue.pop()
    if job is None:
        return WorkerTickResult(job=None, outcome=None)

    outcome = await anyio.to_thread.run_sync(bridge.execute_job, job)

    if events is not None and outcome is not None:
        if outcome.run.status is RunStatus.WAITING_APPROVAL:
            events.append(
                tenant_id=job.tenant_id,
                run_id=job.run_id,
                event=RunEventType.APPROVAL_REQUIRED,
                status=outcome.run.status,
                phase="approval",
                message="Run is waiting for an authorized approval.",
            )
        elif outcome.run.status is RunStatus.COMPLETED:
            events.append(
                tenant_id=job.tenant_id,
                run_id=job.run_id,
                event=RunEventType.COMPLETED,
                status=outcome.run.status,
                phase="complete",
                progress=100,
                message="Run completed.",
            )
        elif outcome.run.status is RunStatus.CANCELLED:
            events.append(
                tenant_id=job.tenant_id,
                run_id=job.run_id,
                event=RunEventType.CANCELLED,
                status=outcome.run.status,
                phase="cancelled",
                message="Run cancelled.",
            )

    return WorkerTickResult(job=job, outcome=outcome)
