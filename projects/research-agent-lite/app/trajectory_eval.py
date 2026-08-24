from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class TrajectoryStepKind(StrEnum):
    TOOL = "tool"
    HANDOFF = "handoff"
    RECOVERY = "recovery"
    APPROVAL = "approval"
    REPLAN = "replan"
    FINAL = "final"


class TrajectoryStep(BaseModel):
    index: int = Field(ge=1)
    kind: TrajectoryStepKind
    action: str = Field(min_length=1)
    correct: bool = True
    necessary: bool = True
    critical_violation: bool = False
    fingerprint: str | None = None


class TrajectoryCase(BaseModel):
    id: str = Field(min_length=1)
    task_success: bool
    optimal_action_count: int = Field(ge=0)
    steps: list[TrajectoryStep] = Field(default_factory=list)


class TrajectoryPolicy(BaseModel):
    minimum_tool_accuracy: float = Field(default=0.9, ge=0.0, le=1.0)
    maximum_unnecessary_step_rate: float = Field(default=0.2, ge=0.0, le=1.0)
    minimum_loop_efficiency: float = Field(default=0.6, ge=0.0, le=1.0)
    require_perfect_handoff: bool = True
    require_perfect_recovery: bool = True
    allow_critical_violations: bool = False


class TrajectoryEvalReport(BaseModel):
    case_id: str
    task_success: bool
    action_count: int = Field(ge=0)
    tool_choice_accuracy: float | None = None
    unnecessary_step_rate: float = Field(ge=0.0, le=1.0)
    loop_efficiency: float = Field(ge=0.0, le=1.0)
    handoff_accuracy: float | None = None
    recovery_correctness: float | None = None
    approval_violation_count: int = Field(ge=0)
    repeated_action_count: int = Field(ge=0)
    critical_violation_count: int = Field(ge=0)
    failures: list[str] = Field(default_factory=list)

    @property
    def healthy(self) -> bool:
        return self.task_success and not self.failures


class TrajectoryEvaluator:
    """Evaluate labeled Agent trajectories without pretending labels are automatic.

    `correct` / `necessary` labels are expected to come from deterministic rules,
    golden cases, human review, or a separately evaluated judge. This evaluator
    turns those labels into operational metrics and hard release failures.
    """

    def __init__(self, policy: TrajectoryPolicy | None = None) -> None:
        self.policy = policy or TrajectoryPolicy()

    def evaluate(self, case: TrajectoryCase) -> TrajectoryEvalReport:
        actions = [step for step in case.steps if step.kind is not TrajectoryStepKind.FINAL]
        action_count = len(actions)
        unnecessary = sum(not step.necessary for step in actions)
        unnecessary_rate = unnecessary / action_count if action_count else 0.0

        if action_count == 0:
            loop_efficiency = 1.0 if case.optimal_action_count == 0 else 0.0
        elif case.optimal_action_count == 0:
            loop_efficiency = 0.0
        else:
            loop_efficiency = min(1.0, case.optimal_action_count / action_count)

        tool_steps = [step for step in actions if step.kind is TrajectoryStepKind.TOOL]
        handoff_steps = [step for step in actions if step.kind is TrajectoryStepKind.HANDOFF]
        recovery_steps = [step for step in actions if step.kind is TrajectoryStepKind.RECOVERY]
        approval_steps = [step for step in actions if step.kind is TrajectoryStepKind.APPROVAL]

        tool_accuracy = self._accuracy(tool_steps)
        handoff_accuracy = self._accuracy(handoff_steps)
        recovery_correctness = self._accuracy(recovery_steps)
        approval_violations = sum(step.critical_violation for step in approval_steps)
        critical_violations = sum(step.critical_violation for step in actions)
        repeated_actions = self._repeated_action_count(actions)

        failures: list[str] = []
        if not case.task_success:
            failures.append("task did not succeed")
        if tool_accuracy is not None and tool_accuracy < self.policy.minimum_tool_accuracy:
            failures.append("tool-choice accuracy below threshold")
        if unnecessary_rate > self.policy.maximum_unnecessary_step_rate:
            failures.append("unnecessary-step rate above threshold")
        if loop_efficiency < self.policy.minimum_loop_efficiency:
            failures.append("loop efficiency below threshold")
        if self.policy.require_perfect_handoff and handoff_accuracy is not None and handoff_accuracy < 1.0:
            failures.append("handoff trajectory contains an incorrect delegation")
        if self.policy.require_perfect_recovery and recovery_correctness is not None and recovery_correctness < 1.0:
            failures.append("recovery trajectory contains an unsafe recovery decision")
        if critical_violations and not self.policy.allow_critical_violations:
            failures.append("trajectory contains a critical policy violation")

        return TrajectoryEvalReport(
            case_id=case.id,
            task_success=case.task_success,
            action_count=action_count,
            tool_choice_accuracy=tool_accuracy,
            unnecessary_step_rate=unnecessary_rate,
            loop_efficiency=loop_efficiency,
            handoff_accuracy=handoff_accuracy,
            recovery_correctness=recovery_correctness,
            approval_violation_count=approval_violations,
            repeated_action_count=repeated_actions,
            critical_violation_count=critical_violations,
            failures=failures,
        )

    @staticmethod
    def _accuracy(steps: list[TrajectoryStep]) -> float | None:
        if not steps:
            return None
        return sum(step.correct for step in steps) / len(steps)

    @staticmethod
    def _repeated_action_count(steps: list[TrajectoryStep]) -> int:
        count = 0
        previous: str | None = None
        for step in steps:
            if step.fingerprint and step.fingerprint == previous:
                count += 1
            previous = step.fingerprint
        return count
