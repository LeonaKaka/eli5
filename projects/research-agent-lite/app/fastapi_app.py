from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .agent_control import RunStatus
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


TenantDep = Annotated[TenantContext, Depends(get_tenant_context)]
BridgeDep = Annotated[ProductionGraphBridge, Depends(get_bridge)]


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


def create_app(*, bridge: ProductionGraphBridge | None = None) -> FastAPI:
    app = FastAPI(
        title="Research Assistant API",
        version="5.2.0",
        description=(
            "HTTP boundary for the provider-neutral Research Assistant. "
            "Run creation enqueues durable work; it does not execute the Agent inline."
        ),
    )
    app.state.bridge = bridge or ProductionGraphBridge()

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
    ) -> RunResponse:
        run = runtime.submit(
            run_id=f"run-{uuid4().hex}",
            tenant_id=tenant.tenant_id,
            objective=body.objective,
            approval_required=body.approval_required,
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

    return app


app = create_app()
