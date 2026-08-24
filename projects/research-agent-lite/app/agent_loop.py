from __future__ import annotations

import inspect
import json
from enum import StrEnum
from typing import Awaitable, Protocol

from pydantic import BaseModel, Field, model_validator

from .agent_control import AgentControlState, LoopGuard, RunStatus, StopReason
from .tools import ToolCall, ToolExecutor, ToolResult


class DecisionKind(StrEnum):
    TOOL = "tool"
    FINAL = "final"


class AgentDecision(BaseModel):
    kind: DecisionKind
    tool_call: ToolCall | None = None
    final_answer: str | None = None
    note: str | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> "AgentDecision":
        if self.kind is DecisionKind.TOOL and self.tool_call is None:
            raise ValueError("tool decision requires tool_call")
        if self.kind is DecisionKind.FINAL and not self.final_answer:
            raise ValueError("final decision requires final_answer")
        return self


class AgentObservation(BaseModel):
    step: int = Field(ge=1)
    source: str = Field(min_length=1)
    ok: bool
    output: object | None = None
    error_type: str | None = None
    error_message: str | None = None

    @classmethod
    def from_tool_result(cls, *, step: int, tool_name: str, result: ToolResult) -> "AgentObservation":
        return cls(
            step=step,
            source=tool_name,
            ok=result.ok,
            output=result.output,
            error_type=result.error.type if result.error else None,
            error_message=result.error.message if result.error else None,
        )


class AgentTraceEvent(BaseModel):
    step: int = Field(ge=1)
    kind: str = Field(min_length=1)
    detail: str = Field(min_length=1)


class AgentContext(BaseModel):
    objective: str = Field(min_length=1)
    control: AgentControlState = Field(default_factory=AgentControlState)
    observations: list[AgentObservation] = Field(default_factory=list)
    trace: list[AgentTraceEvent] = Field(default_factory=list)


class AgentRunResult(BaseModel):
    status: RunStatus
    final_answer: str | None = None
    stop_reason: StopReason | None = None
    trace: list[AgentTraceEvent] = Field(default_factory=list)
    observations: list[AgentObservation] = Field(default_factory=list)
    tool_calls: int = Field(ge=0)
    failures: int = Field(ge=0)


class DecisionMaker(Protocol):
    def decide(self, context: AgentContext) -> AgentDecision | Awaitable[AgentDecision]: ...


class AgentLoop:
    """Minimal observe/decide/act/update loop with an application-side guard."""

    def __init__(
        self,
        *,
        decision_maker: DecisionMaker,
        tool_executor: ToolExecutor,
        guard: LoopGuard | None = None,
    ) -> None:
        self.decision_maker = decision_maker
        self.tool_executor = tool_executor
        self.guard = guard or LoopGuard()

    async def run(self, objective: str, *, approved: bool = False) -> AgentRunResult:
        context = AgentContext(objective=objective)

        while True:
            reason = self.guard.before_decision(context.control)
            if reason is not None:
                return self._stop(context, reason)

            decision = self.decision_maker.decide(context)
            if inspect.isawaitable(decision):
                decision = await decision

            context.control.step_count += 1
            step = context.control.step_count

            if decision.kind is DecisionKind.FINAL:
                context.control.status = RunStatus.COMPLETED
                context.control.stop_reason = StopReason.FINAL_ANSWER
                context.trace.append(
                    AgentTraceEvent(step=step, kind="final", detail=decision.final_answer or "")
                )
                return AgentRunResult(
                    status=context.control.status,
                    final_answer=decision.final_answer,
                    stop_reason=context.control.stop_reason,
                    trace=context.trace,
                    observations=context.observations,
                    tool_calls=context.control.tool_calls,
                    failures=context.control.failures,
                )

            call = decision.tool_call
            assert call is not None
            fingerprint = action_fingerprint(call)
            context.trace.append(
                AgentTraceEvent(
                    step=step,
                    kind="decision",
                    detail=f"tool:{call.name} args={json.dumps(call.arguments, sort_keys=True, ensure_ascii=False)}",
                )
            )

            reason = self.guard.before_tool(context.control, fingerprint)
            if reason is not None:
                return self._stop(context, reason)

            context.control.status = RunStatus.WAITING_TOOL
            result = await self.tool_executor.execute(call, approved=approved)
            context.control.tool_calls += 1
            context.control.action_fingerprints.append(fingerprint)
            if not result.ok:
                context.control.failures += 1

            observation = AgentObservation.from_tool_result(
                step=step,
                tool_name=call.name,
                result=result,
            )
            context.observations.append(observation)
            context.trace.append(
                AgentTraceEvent(
                    step=step,
                    kind="observation",
                    detail=(
                        f"{call.name} ok output={result.output!r}"
                        if result.ok
                        else f"{call.name} failed type={result.error.type if result.error else 'unknown'}"
                    ),
                )
            )
            context.control.status = RunStatus.RUNNING

            reason = self.guard.after_tool(context.control)
            if reason is not None:
                return self._stop(context, reason)

    @staticmethod
    def _stop(context: AgentContext, reason: StopReason) -> AgentRunResult:
        context.control.status = RunStatus.STOPPED
        context.control.stop_reason = reason
        event_step = max(1, context.control.step_count)
        context.trace.append(
            AgentTraceEvent(step=event_step, kind="stop", detail=reason.value)
        )
        return AgentRunResult(
            status=context.control.status,
            final_answer=None,
            stop_reason=reason,
            trace=context.trace,
            observations=context.observations,
            tool_calls=context.control.tool_calls,
            failures=context.control.failures,
        )


def action_fingerprint(call: ToolCall) -> str:
    args = json.dumps(call.arguments, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"{call.name}:{args}"


class ScriptedDecisionMaker:
    """Deterministic teaching adapter for tests and offline demos."""

    def __init__(self, decisions: list[AgentDecision]) -> None:
        if not decisions:
            raise ValueError("at least one decision is required")
        self.decisions = decisions
        self.index = 0

    def decide(self, context: AgentContext) -> AgentDecision:
        del context
        if self.index >= len(self.decisions):
            return self.decisions[-1]
        decision = self.decisions[self.index]
        self.index += 1
        return decision
