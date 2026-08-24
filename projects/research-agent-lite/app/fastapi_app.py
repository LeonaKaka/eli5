from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated
from uuid import uuid4

import anyio
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .agent_control import RunStatus
from .fastapi_streaming import InMemoryRunEventStore, RunEventType
from .langgraph_production import ProductionGraphBridge
from .production import RunRecord


class CreateRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective: str = Field(min_length=1, max_length=4000)
    approval_required: bool = False

    @field_validator("objective")
    @classmethod
    def normalize_objective(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not normalized:
            raise ValueError("objective must contain non-whitespace text")
        return normalized


class RunResponse(BaseModel):
    """Public HTTP projection of RunRecord.

    Internal tenant ids, checkpoint ids, approval request ids and budgets are
    deliberately excluded from the public response contract.
    """

    id: str
    objective: str
    status: RunStatus
    revision: int
    cancel_requested: bool

    @classmethod
    def from_record(cls, record: RunRecord) -> "RunResponse":
        return cls(
            id=record.id,
            objective=record.objective,
            status=record.status,
            revision=record.revision,
            cancel_requested=record.cancel_requested,
        )


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str


@dataclass(frozen=True)
class RunStreamContext:
    tenant_id: str
    cursor: int


async def get_tenant_context(
    x_tenant_id: Annotated[str, Header(alias="X-Tenant-ID", min_length=1, max_length=128)],
) -> TenantContext:
    """Teaching tenant dependency.

    The header is only a boundary-input demo. Lesson 06 replaces this trust model
    with authenticated identity + authorization; clients must not be allowed to
    self-assert arbitrary tenant ids in a real deployment.
    """

    tenant_id = x_tenant_id.strip()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="X-Tenant-ID must not be blank",
        )
    return TenantContext(tenant_id=tenant_id)


def get_bridge(request: Request) -> ProductionGraphBridge:
    return request.app.state.bridge


def get_run_events(request: Request) -> InMemoryRunEventStore:
    return request.app.state.run_events


TenantDep = Annotated[TenantContext, Depends(get_tenant_context)]
BridgeDep = Annotated[ProductionGraphBridge, Depends(get_bridge)]
RunEventsDep = Annotated[InMemoryRunEventStore, Depends(get_run_events)]


_TERMINAL_STATUSES = {
    RunStatus.COMPLETED,
    RunStatus.FAILED,
    RunStatus.STOPPED,
    RunStatus.CANCELLED,
}


def _load_public_run(
    bridge: ProductionGraphBridge,
    *,
    run_id: str,
    tenant_id: str,
) -> RunRecord:
    try:
        return bridge.control.store.get(run_id, tenant_id=tenant_id)
    except (KeyError, PermissionError) as exc:
        # Avoid telling one tenant whether another tenant's run id exists.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="run not found",
        ) from exc


def _parse_last_event_id(raw: str | None) -> int:
    if raw is None or not raw.strip():
        return 0
    try:
        value = int(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Last-Event-ID must be a non-negative integer",
        ) from exc
    if value < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Last-Event-ID must be a non-negative integer",
        )
    return value


async def get_run_stream_context(
    run_id: str,
    tenant: TenantDep,
    runtime: BridgeDep,
    events: RunEventsDep,
    last_event_id: Annotated[
        str | None,
        Header(alias="Last-Event-ID", description="Resume after this SSE event id"),
    ] = None,
) -> RunStreamContext:
    """Validate stream ownership/cursor before the SSE response starts."""

    _load_public_run(
        runtime,
        run_id=run_id,
        tenant_id=tenant.tenant_id,
    )
    cursor = _parse_last_event_id(last_event_id)
    oldest = events.oldest_sequence(tenant_id=tenant.tenant_id, run_id=run_id)
    if last_event_id is not None and oldest is not None and cursor < oldest - 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="requested event history is no longer retained; refetch Run state",
        )
    return RunStreamContext(tenant_id=tenant.tenant_id, cursor=cursor)


RunStreamDep = Annotated[RunStreamContext, Depends(get_run_stream_context)]


def create_app(
    *,
    bridge: ProductionGraphBridge | None = None,
    event_store: InMemoryRunEventStore | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Research Assistant API",
        version="5.4.0",
        description=(
            "HTTP boundary for the provider-neutral Research Assistant. "
            "Run creation enqueues durable work; it does not execute the Agent inline."
        ),
    )
    app.state.bridge = bridge or ProductionGraphBridge()
    app.state.run_events = event_store or InMemoryRunEventStore()

    @app.post(
        "/runs",
        response_model=RunResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["runs"],
        summary="Create a queued Research Assistant run",
    )
    async def create_run(
        body: CreateRunRequest,
        tenant: TenantDep,
        runtime: BridgeDep,
        events: RunEventsDep,
    ) -> RunResponse:
        run = runtime.submit(
            run_id=f"run-{uuid4().hex}",
            tenant_id=tenant.tenant_id,
            objective=body.objective,
            approval_required=body.approval_required,
        )
        events.append(
            tenant_id=tenant.tenant_id,
            run_id=run.id,
            event=RunEventType.RUN_CREATED,
            status=run.status,
            phase="queued",
            progress=0,
            message="Run accepted and queued for durable worker execution.",
        )
        return RunResponse.from_record(run)

    @app.get(
        "/runs/{run_id}",
        response_model=RunResponse,
        tags=["runs"],
        summary="Read one tenant-scoped run",
    )
    async def get_run(
        run_id: str,
        tenant: TenantDep,
        runtime: BridgeDep,
    ) -> RunResponse:
        record = _load_public_run(
            runtime,
            run_id=run_id,
            tenant_id=tenant.tenant_id,
        )
        return RunResponse.from_record(record)

    @app.get(
        "/runs/{run_id}/stream",
        response_class=EventSourceResponse,
        tags=["runs"],
        summary="Stream client-safe Run events with SSE",
    )
    async def stream_run(
        run_id: str,
        request: Request,
        stream: RunStreamDep,
        runtime: BridgeDep,
        events: RunEventsDep,
        follow: Annotated[
            bool,
            Query(description="Keep following future events; false is useful for replay/tests"),
        ] = True,
    ) -> AsyncIterator[ServerSentEvent]:
        cursor = stream.cursor
        while True:
            batch = events.list_after(
                tenant_id=stream.tenant_id,
                run_id=run_id,
                after_sequence=cursor,
            )
            for item in batch:
                cursor = item.sequence
                yield ServerSentEvent(
                    id=str(item.sequence),
                    event=item.event.value,
                    data=item.public_data(),
                )

            if not follow:
                return

            record = runtime.control.store.get(
                run_id,
                tenant_id=stream.tenant_id,
            )
            if record.status in _TERMINAL_STATUSES:
                return
            if await request.is_disconnected():
                return
            await anyio.sleep(0.25)

    return app


app = create_app()
