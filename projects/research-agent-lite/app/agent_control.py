from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class RunStatus(StrEnum):
    RUNNING = "running"
    WAITING_TOOL = "waiting_tool"
    WAITING_APPROVAL = "waiting_approval"
    PAUSED = "paused"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StopReason(StrEnum):
    FINAL_ANSWER = "final_answer"
    MAX_STEPS = "max_steps"
    TOOL_BUDGET = "tool_budget"
    FAILURE_BUDGET = "failure_budget"
    REPEATED_ACTION = "repeated_action"
    NO_PROGRESS = "no_progress"
    CANCELLED = "cancelled"


class RunBudget(BaseModel):
    max_steps: int = Field(default=8, ge=1)
    max_tool_calls: int = Field(default=6, ge=0)
    max_failures: int = Field(default=2, ge=0)
    max_same_action: int = Field(default=2, ge=1)


class AgentControlState(BaseModel):
    """Small control-plane state kept separate from model conversation state."""

    status: RunStatus = RunStatus.RUNNING
    step_count: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    failures: int = Field(default=0, ge=0)
    action_fingerprints: list[str] = Field(default_factory=list)
    stop_reason: StopReason | None = None


class LoopGuard:
    """Application-side hard limits for an agent run.

    Prompts may *ask* a model to avoid loops, but these checks are enforced
    outside the model and can terminate a run independently of model output.
    """

    def __init__(self, budget: RunBudget | None = None) -> None:
        self.budget = budget or RunBudget()

    def before_decision(self, state: AgentControlState) -> StopReason | None:
        if state.step_count >= self.budget.max_steps:
            return StopReason.MAX_STEPS
        return None

    def before_tool(self, state: AgentControlState, fingerprint: str) -> StopReason | None:
        if state.tool_calls >= self.budget.max_tool_calls:
            return StopReason.TOOL_BUDGET
        if self._consecutive_count(state.action_fingerprints, fingerprint) >= self.budget.max_same_action:
            return StopReason.REPEATED_ACTION
        return None

    def after_tool(self, state: AgentControlState) -> StopReason | None:
        if state.failures > self.budget.max_failures:
            return StopReason.FAILURE_BUDGET
        return None

    @staticmethod
    def _consecutive_count(history: list[str], fingerprint: str) -> int:
        count = 0
        for item in reversed(history):
            if item != fingerprint:
                break
            count += 1
        return count
