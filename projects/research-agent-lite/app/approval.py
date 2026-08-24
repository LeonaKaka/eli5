from __future__ import annotations

import json
from enum import StrEnum

from pydantic import BaseModel, Field

from .agent_control import RunStatus
from .tools import Permission, ToolCall, ToolExecutor, ToolRegistry, ToolResult


class ApprovalAction(StrEnum):
    AUTO_EXECUTE = "auto_execute"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXECUTED = "executed"


class ApprovalCheck(BaseModel):
    action: ApprovalAction
    reason: str
    permission: Permission | None = None


class ApprovalRequest(BaseModel):
    id: str = Field(min_length=1)
    call: ToolCall
    permission: Permission
    fingerprint: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    status: ApprovalStatus = ApprovalStatus.PENDING
    reviewer: str | None = None


class ApprovalExecution(BaseModel):
    run_status: RunStatus
    check: ApprovalCheck
    request: ApprovalRequest | None = None
    tool_result: ToolResult | None = None


class ApprovalPolicy:
    """Application-side policy for deciding which tool calls may execute."""

    def __init__(self, *, destructive_requires_approval: bool = False) -> None:
        self.destructive_requires_approval = destructive_requires_approval

    def evaluate(self, permission: Permission) -> ApprovalCheck:
        if permission is Permission.READ_ONLY:
            return ApprovalCheck(
                action=ApprovalAction.AUTO_EXECUTE,
                permission=permission,
                reason="read-only action is allowed to execute automatically",
            )
        if permission is Permission.SIDE_EFFECT:
            return ApprovalCheck(
                action=ApprovalAction.REQUIRE_APPROVAL,
                permission=permission,
                reason="side-effect action requires explicit human approval",
            )
        if self.destructive_requires_approval:
            return ApprovalCheck(
                action=ApprovalAction.REQUIRE_APPROVAL,
                permission=permission,
                reason="destructive action is permitted only after explicit approval",
            )
        return ApprovalCheck(
            action=ApprovalAction.DENY,
            permission=permission,
            reason="destructive actions are denied by the current policy",
        )


class ApprovalManager:
    """Interrupt execution before side effects and resume the exact approved call.

    Approval binds to a canonical fingerprint of the proposed call. The model is
    not asked to regenerate the action after approval; the stored ToolCall is the
    one that is executed, which avoids approval/execution drift.
    """

    def __init__(
        self,
        *,
        registry: ToolRegistry,
        executor: ToolExecutor,
        policy: ApprovalPolicy | None = None,
    ) -> None:
        self.registry = registry
        self.executor = executor
        self.policy = policy or ApprovalPolicy()
        self._requests: dict[str, ApprovalRequest] = {}

    async def submit(self, call: ToolCall) -> ApprovalExecution:
        registered = self.registry.get(call.name)
        if registered is None:
            return ApprovalExecution(
                run_status=RunStatus.STOPPED,
                check=ApprovalCheck(action=ApprovalAction.DENY, reason=f"unknown tool: {call.name}"),
            )

        check = self.policy.evaluate(registered.spec.permission)
        if check.action is ApprovalAction.DENY:
            return ApprovalExecution(run_status=RunStatus.STOPPED, check=check)
        if check.action is ApprovalAction.AUTO_EXECUTE:
            result = await self.executor.execute(call, approved=False)
            return ApprovalExecution(
                run_status=RunStatus.RUNNING,
                check=check,
                tool_result=result,
            )

        request_id = f"approval:{call.id}"
        if request_id in self._requests:
            raise ValueError(f"approval request already exists: {request_id}")
        request = ApprovalRequest(
            id=request_id,
            call=call.model_copy(deep=True),
            permission=registered.spec.permission,
            fingerprint=tool_call_fingerprint(call),
            reason=check.reason,
        )
        self._requests[request_id] = request
        return ApprovalExecution(
            run_status=RunStatus.WAITING_APPROVAL,
            check=check,
            request=request,
        )

    async def resume(
        self,
        request_id: str,
        *,
        approved: bool,
        reviewer: str,
    ) -> ApprovalExecution:
        request = self._requests.get(request_id)
        if request is None:
            raise KeyError(f"unknown approval request: {request_id}")
        if request.status is not ApprovalStatus.PENDING:
            raise ValueError(f"approval request is already resolved: {request_id}")
        if not reviewer.strip():
            raise ValueError("reviewer is required")

        current_fingerprint = tool_call_fingerprint(request.call)
        if current_fingerprint != request.fingerprint:
            raise ValueError(
                f"approval request fingerprint mismatch: {request_id}; proposed action changed after review was requested"
            )

        if not approved:
            resolved = request.model_copy(
                update={"status": ApprovalStatus.DENIED, "reviewer": reviewer}
            )
            self._requests[request_id] = resolved
            return ApprovalExecution(
                run_status=RunStatus.STOPPED,
                check=ApprovalCheck(
                    action=ApprovalAction.DENY,
                    permission=request.permission,
                    reason="human reviewer denied the proposed action",
                ),
                request=resolved,
            )

        approved_request = request.model_copy(
            update={"status": ApprovalStatus.APPROVED, "reviewer": reviewer}
        )
        self._requests[request_id] = approved_request
        result = await self.executor.execute(approved_request.call, approved=True)
        executed = approved_request.model_copy(update={"status": ApprovalStatus.EXECUTED})
        self._requests[request_id] = executed
        return ApprovalExecution(
            run_status=RunStatus.RUNNING if result.ok else RunStatus.FAILED,
            check=ApprovalCheck(
                action=ApprovalAction.AUTO_EXECUTE,
                permission=request.permission,
                reason="the exact approved action was resumed and executed",
            ),
            request=executed,
            tool_result=result,
        )

    def get(self, request_id: str) -> ApprovalRequest | None:
        return self._requests.get(request_id)


def tool_call_fingerprint(call: ToolCall) -> str:
    arguments = json.dumps(call.arguments, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"{call.name}:{arguments}"
