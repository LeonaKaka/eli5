from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated
from uuid import uuid4

import anyio
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .agent_control import RunStatus
from .fastapi_commands import (
    IdempotentCommandResult,
    InMemoryIdempotencyStore,
    command_fingerprint,
    enforce_revision_precondition,
    etag_for_revision,
    normalize_idempotency_key,
    parse_if_match,
)
from .fastapi_errors import install_error_layer, problem_responses
from .fastapi_security import (
    DemoTokenAuthenticator,
    RunApprovePrincipal,
    RunCancelPrincipal,
    RunCreatePrincipal,
    RunReadPrincipal,
)
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


class ApprovalDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class ResolveApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: ApprovalDecision


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
class RunStreamContext:
    tenant_id: str
    cursor: int


def get_bridge(request: Request) -> ProductionGraphBridge:
    return request.app.state.bridge


def get_run_events(request: Request) -> InMemoryRunEventStore:
    return request.app.state.run_events


def get_idempotency_store(request: Request) -> InMemoryIdempotencyStore:
    return request.app.state.idempotency_store


BridgeDep = Annotated[ProductionGraphBridge, Depends(get_bridge)]
RunEventsDep = Annotated[InMemoryRunEventStore, Depends(get_run_events)]
IdempotencyDep = Annotated[InMemoryIdempotencyStore, Depends(get_idempotency_store)]


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="run not found",
        ) from exc


def _set_run_headers(response: Response, record: RunRecord) -> None:
    response.headers["ETag"] = etag_for_revision(record.revision)


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
    principal: RunReadPrincipal,
    runtime: BridgeDep,
    events: RunEventsDep,
    last_event_id: Annotated[
        str | None,
        Header(alias="Last-Event-ID", description="Resume after this SSE event id"),
    ] = None,
) -> RunStreamContext:
    """Authorize Run access and validate cursor before SSE headers are sent."""

    _load_public_run(
        runtime,
        run_id=run_id,
        tenant_id=principal.tenant_id,
    )
    cursor = _parse_last_event_id(last_event_id)
    oldest = events.oldest_sequence(tenant_id=principal.tenant_id, run_id=run_id)
    if last_event_id is not None and oldest is not None and cursor < oldest - 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="requested event history is no longer retained; refetch Run state",
        )
    return RunStreamContext(tenant_id=principal.tenant_id, cursor=cursor)


RunStreamDep = Annotated[RunStreamContext, Depends(get_run_stream_context)]


def create_app(
    *,
    bridge: ProductionGraphBridge | None = None,
    event_store: InMemoryRunEventStore | None = None,
    idempotency_store: InMemoryIdempotencyStore | None = None,
    authenticator: DemoTokenAuthenticator | None = None,
    allowed_origins: tuple[str, ...] = ("https://app.example.test",),
) -> FastAPI:
    app = FastAPI(
        title="Research Assistant API",
        version="5.8.0",
        description=(
            "HTTP boundary for the provider-neutral Research Assistant. "
            "Run creation enqueues durable work; mutating commands use auth, "
            "revision preconditions and idempotency keys; errors use one public contract."
        ),
    )
    app.state.bridge = bridge or ProductionGraphBridge()
    app.state.run_events = event_store or InMemoryRunEventStore()
    app.state.idempotency_store = idempotency_store or InMemoryIdempotencyStore()
    app.state.authenticator = authenticator or DemoTokenAuthenticator()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(allowed_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Idempotency-Key",
            "If-Match",
            "Last-Event-ID",
        ],
        expose_headers=["ETag", "Idempotency-Replayed", "X-Request-ID"],
    )
    install_error_layer(app)

    @app.post(
        "/runs",
        response_model=RunResponse,
        status_code=status.HTTP_201_CREATED,
        responses=problem_responses(401, 403, 422, 500),
        tags=["runs"],
        summary="Create a queued Research Assistant run",
    )
    async def create_run(
        body: CreateRunRequest,
        response: Response,
        principal: RunCreatePrincipal,
        runtime: BridgeDep,
        events: RunEventsDep,
    ) -> RunResponse:
        run = runtime.submit(
            run_id=f"run-{uuid4().hex}",
            tenant_id=principal.tenant_id,
            objective=body.objective,
            approval_required=body.approval_required,
        )
        events.append(
            tenant_id=principal.tenant_id,
            run_id=run.id,
            event=RunEventType.RUN_CREATED,
            status=run.status,
            phase="queued",
            progress=0,
            message="Run accepted and queued for durable worker execution.",
        )
        _set_run_headers(response, run)
        return RunResponse.from_record(run)

    @app.get(
        "/runs/{run_id}",
        response_model=RunResponse,
        responses=problem_responses(401, 403, 404, 500),
        tags=["runs"],
        summary="Read one authorized tenant-scoped run",
    )
    async def get_run(
        run_id: str,
        response: Response,
        principal: RunReadPrincipal,
        runtime: BridgeDep,
    ) -> RunResponse:
        record = _load_public_run(
            runtime,
            run_id=run_id,
            tenant_id=principal.tenant_id,
        )
        _set_run_headers(response, record)
        return RunResponse.from_record(record)

    @app.get(
        "/runs/{run_id}/stream",
        response_class=EventSourceResponse,
        responses=problem_responses(400, 401, 403, 404, 409, 422, 500),
        tags=["runs"],
        summary="Stream authorized client-safe Run events with SSE",
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

    @app.post(
        "/runs/{run_id}/approvals/{approval_request_id}",
        response_model=RunResponse,
        responses=problem_responses(400, 401, 403, 404, 409, 412, 422, 428, 500),
        tags=["commands"],
        summary="Approve or reject one exact paused approval request",
    )
    async def resolve_approval(
        run_id: str,
        approval_request_id: str,
        body: ResolveApprovalRequest,
        response: Response,
        principal: RunApprovePrincipal,
        runtime: BridgeDep,
        events: RunEventsDep,
        idempotency: IdempotencyDep,
        idempotency_key_raw: Annotated[
            str,
            Header(alias="Idempotency-Key", min_length=1, max_length=200),
        ],
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> RunResponse:
        current = _load_public_run(
            runtime,
            run_id=run_id,
            tenant_id=principal.tenant_id,
        )
        expected_revision = parse_if_match(if_match)
        idempotency_key = normalize_idempotency_key(idempotency_key_raw)
        fingerprint = command_fingerprint(
            operation="resolve_approval",
            run_id=run_id,
            target_id=approval_request_id,
            expected_revision=expected_revision,
            body=body.model_dump(mode="json"),
        )

        def execute() -> IdempotentCommandResult:
            enforce_revision_precondition(
                current_revision=current.revision,
                expected_revision=expected_revision,
            )
            try:
                updated = runtime.resolve_approval(
                    run_id,
                    tenant_id=principal.tenant_id,
                    approval_request_id=approval_request_id,
                    approved=body.decision is ApprovalDecision.APPROVE,
                    actor_authorized=True,
                )
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=str(exc),
                ) from exc

            if body.decision is ApprovalDecision.APPROVE:
                events.append(
                    tenant_id=principal.tenant_id,
                    run_id=run_id,
                    event=RunEventType.APPROVAL_RESOLVED,
                    status=updated.status,
                    phase="approval",
                    message="Approval accepted; a durable resume job was queued.",
                )
            else:
                events.append(
                    tenant_id=principal.tenant_id,
                    run_id=run_id,
                    event=RunEventType.CANCELLED,
                    status=updated.status,
                    phase="approval_rejected",
                    message="Approval rejected; Run was cancelled.",
                )
            public = RunResponse.from_record(updated)
            return IdempotentCommandResult(
                payload=public.model_dump(mode="json"),
                etag=etag_for_revision(updated.revision),
            )

        result = idempotency.execute_once(
            tenant_id=principal.tenant_id,
            operation="resolve_approval",
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
            execute=execute,
        )
        response.headers["ETag"] = result.etag
        response.headers["Idempotency-Replayed"] = "true" if result.replayed else "false"
        return RunResponse.model_validate(result.payload)

    @app.post(
        "/runs/{run_id}/cancel",
        response_model=RunResponse,
        responses=problem_responses(400, 401, 403, 404, 409, 412, 422, 428, 500),
        tags=["commands"],
        summary="Request idempotent cancellation of one Run",
    )
    async def cancel_run(
        run_id: str,
        response: Response,
        principal: RunCancelPrincipal,
        runtime: BridgeDep,
        events: RunEventsDep,
        idempotency: IdempotencyDep,
        idempotency_key_raw: Annotated[
            str,
            Header(alias="Idempotency-Key", min_length=1, max_length=200),
        ],
        if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    ) -> RunResponse:
        current = _load_public_run(
            runtime,
            run_id=run_id,
            tenant_id=principal.tenant_id,
        )
        expected_revision = parse_if_match(if_match)
        idempotency_key = normalize_idempotency_key(idempotency_key_raw)
        fingerprint = command_fingerprint(
            operation="cancel_run",
            run_id=run_id,
            expected_revision=expected_revision,
        )

        def execute() -> IdempotentCommandResult:
            enforce_revision_precondition(
                current_revision=current.revision,
                expected_revision=expected_revision,
            )
            if current.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.STOPPED}:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"terminal Run in status {current.status.value} cannot be cancelled",
                )
            updated = runtime.control.request_cancel(
                run_id,
                tenant_id=principal.tenant_id,
            )
            events.append(
                tenant_id=principal.tenant_id,
                run_id=run_id,
                event=(
                    RunEventType.CANCELLED
                    if updated.status is RunStatus.CANCELLED
                    else RunEventType.CANCEL_REQUESTED
                ),
                status=updated.status,
                phase="cancel",
                message=(
                    "Run cancelled before active execution."
                    if updated.status is RunStatus.CANCELLED
                    else "Cancellation requested; Worker must stop at a safe boundary."
                ),
            )
            public = RunResponse.from_record(updated)
            return IdempotentCommandResult(
                payload=public.model_dump(mode="json"),
                etag=etag_for_revision(updated.revision),
            )

        result = idempotency.execute_once(
            tenant_id=principal.tenant_id,
            operation="cancel_run",
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
            execute=execute,
        )
        response.headers["ETag"] = result.etag
        response.headers["Idempotency-Replayed"] = "true" if result.replayed else "false"
        return RunResponse.model_validate(result.payload)

    return app


app = create_app()
