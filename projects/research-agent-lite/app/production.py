from __future__ import annotations

from collections import deque
from enum import StrEnum

from pydantic import BaseModel, Field

from .agent_control import RunBudget, RunStatus


class JobKind(StrEnum):
    START = "start"
    RESUME = "resume"


class RunRecord(BaseModel):
    id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    status: RunStatus = RunStatus.PAUSED
    revision: int = Field(default=1, ge=1)
    budget: RunBudget = Field(default_factory=RunBudget)
    cancel_requested: bool = False
    current_checkpoint_id: str | None = None
    approval_request_id: str | None = None
    owner_agent: str = "supervisor"
    trace_events: int = Field(default=0, ge=0)


class RunJob(BaseModel):
    id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    kind: JobKind
    expected_revision: int = Field(ge=1)
    attempt: int = Field(default=1, ge=1)


class ClaimResult(BaseModel):
    accepted: bool
    reason: str
    record: RunRecord


class InMemoryRunStore:
    """Teaching store with tenant scoping and optimistic revision checks."""

    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}

    def create(self, record: RunRecord) -> RunRecord:
        if record.id in self._runs:
            raise ValueError(f"run already exists: {record.id}")
        stored = record.model_copy(deep=True)
        self._runs[record.id] = stored
        return stored.model_copy(deep=True)

    def get(self, run_id: str, *, tenant_id: str) -> RunRecord:
        record = self._runs.get(run_id)
        if record is None:
            raise KeyError(f"unknown run: {run_id}")
        if record.tenant_id != tenant_id:
            raise PermissionError("run does not belong to this tenant")
        return record.model_copy(deep=True)

    def update(
        self,
        run_id: str,
        *,
        tenant_id: str,
        expected_revision: int,
        **changes: object,
    ) -> RunRecord:
        current = self.get(run_id, tenant_id=tenant_id)
        if current.revision != expected_revision:
            raise RuntimeError(
                f"stale run revision: expected {expected_revision}, current {current.revision}"
            )
        changes["revision"] = current.revision + 1
        updated = current.model_copy(deep=True, update=changes)
        self._runs[run_id] = updated
        return updated.model_copy(deep=True)


class InMemoryRunQueue:
    """Small queue. Real queues may redeliver; worker claims must still be idempotent."""

    def __init__(self) -> None:
        self._items: deque[RunJob] = deque()

    def enqueue(self, job: RunJob) -> None:
        self._items.append(job.model_copy(deep=True))

    def pop(self) -> RunJob | None:
        if not self._items:
            return None
        return self._items.popleft()

    def __len__(self) -> int:
        return len(self._items)


class ProductionControlPlane:
    """Provider-neutral run/queue control-plane contract for Agent v4.0.

    It deliberately does not execute the Agent itself. A production worker would
    combine this state contract with durable checkpoints, approval, tools and
    traces. The in-memory adapters exist to make concurrency/cancellation rules
    deterministic in tests. Lease/heartbeat expiry is assumed to be detected by
    infrastructure; `requeue_abandoned()` models what happens after that fact.

    A claimed run revision acts like an optimistic worker token: every worker-side
    state transition must present the revision it actually claimed. A stale worker
    therefore cannot wake up later and overwrite a newer recovery worker.
    """

    def __init__(
        self,
        *,
        store: InMemoryRunStore | None = None,
        queue: InMemoryRunQueue | None = None,
    ) -> None:
        self.store = store or InMemoryRunStore()
        self.queue = queue or InMemoryRunQueue()

    def submit(
        self,
        *,
        run_id: str,
        tenant_id: str,
        objective: str,
        budget: RunBudget | None = None,
    ) -> RunRecord:
        record = self.store.create(
            RunRecord(
                id=run_id,
                tenant_id=tenant_id,
                objective=objective,
                status=RunStatus.PAUSED,
                budget=budget or RunBudget(),
            )
        )
        self.queue.enqueue(
            RunJob(
                id=f"{run_id}:start:r{record.revision}",
                run_id=run_id,
                tenant_id=tenant_id,
                kind=JobKind.START,
                expected_revision=record.revision,
            )
        )
        return record

    def claim(self, job: RunJob) -> ClaimResult:
        record = self.store.get(job.run_id, tenant_id=job.tenant_id)
        if record.cancel_requested or record.status is RunStatus.CANCELLED:
            return ClaimResult(accepted=False, reason="run is cancelled", record=record)
        if record.revision != job.expected_revision:
            return ClaimResult(accepted=False, reason="stale or duplicate job delivery", record=record)
        if record.status is not RunStatus.PAUSED:
            return ClaimResult(
                accepted=False,
                reason=f"run is not claimable from status {record.status.value}",
                record=record,
            )
        updated = self.store.update(
            record.id,
            tenant_id=record.tenant_id,
            expected_revision=record.revision,
            status=RunStatus.RUNNING,
        )
        return ClaimResult(accepted=True, reason="worker claimed run revision", record=updated)

    def request_cancel(self, run_id: str, *, tenant_id: str) -> RunRecord:
        current = self.store.get(run_id, tenant_id=tenant_id)
        if current.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            return current
        return self.store.update(
            run_id,
            tenant_id=tenant_id,
            expected_revision=current.revision,
            cancel_requested=True,
            status=RunStatus.CANCELLED,
        )

    def requeue_abandoned(
        self,
        run_id: str,
        *,
        tenant_id: str,
        expected_revision: int,
        checkpoint_id: str,
        attempt: int = 2,
    ) -> RunRecord:
        """Requeue a RUNNING run after an external lease/heartbeat watchdog fires."""
        current = self.store.get(run_id, tenant_id=tenant_id)
        if current.cancel_requested or current.status is RunStatus.CANCELLED:
            raise ValueError("cancelled run must not be requeued")
        if current.status is not RunStatus.RUNNING:
            raise ValueError("only an abandoned running run can be requeued")
        if current.revision != expected_revision:
            raise RuntimeError(
                f"stale abandoned-run revision: expected {expected_revision}, current {current.revision}"
            )
        updated = self.store.update(
            run_id,
            tenant_id=tenant_id,
            expected_revision=expected_revision,
            status=RunStatus.PAUSED,
            current_checkpoint_id=checkpoint_id,
        )
        self.queue.enqueue(
            RunJob(
                id=f"{run_id}:recovery:r{updated.revision}:a{attempt}",
                run_id=run_id,
                tenant_id=tenant_id,
                kind=JobKind.RESUME,
                expected_revision=updated.revision,
                attempt=attempt,
            )
        )
        return updated

    def pause_for_approval(
        self,
        run_id: str,
        *,
        tenant_id: str,
        expected_revision: int,
        approval_request_id: str,
        checkpoint_id: str,
    ) -> RunRecord:
        current = self.store.get(run_id, tenant_id=tenant_id)
        if current.status is not RunStatus.RUNNING:
            raise ValueError("only a running run can wait for approval")
        return self.store.update(
            run_id,
            tenant_id=tenant_id,
            expected_revision=expected_revision,
            status=RunStatus.WAITING_APPROVAL,
            approval_request_id=approval_request_id,
            current_checkpoint_id=checkpoint_id,
        )

    def enqueue_resume_after_approval(
        self,
        run_id: str,
        *,
        tenant_id: str,
        approval_request_id: str,
    ) -> RunRecord:
        current = self.store.get(run_id, tenant_id=tenant_id)
        if current.status is not RunStatus.WAITING_APPROVAL:
            raise ValueError("run is not waiting for approval")
        if current.approval_request_id != approval_request_id:
            raise ValueError("approval request does not match the paused run")
        updated = self.store.update(
            run_id,
            tenant_id=tenant_id,
            expected_revision=current.revision,
            status=RunStatus.PAUSED,
            approval_request_id=None,
        )
        self.queue.enqueue(
            RunJob(
                id=f"{run_id}:resume:r{updated.revision}",
                run_id=run_id,
                tenant_id=tenant_id,
                kind=JobKind.RESUME,
                expected_revision=updated.revision,
            )
        )
        return updated

    def finish(
        self,
        run_id: str,
        *,
        tenant_id: str,
        expected_revision: int,
        trace_events: int,
    ) -> RunRecord:
        current = self.store.get(run_id, tenant_id=tenant_id)
        if current.status is not RunStatus.RUNNING:
            raise ValueError("only a running run can complete")
        return self.store.update(
            run_id,
            tenant_id=tenant_id,
            expected_revision=expected_revision,
            status=RunStatus.COMPLETED,
            trace_events=trace_events,
        )
