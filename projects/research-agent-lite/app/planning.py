from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class PlanStepStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class ReplanReason(StrEnum):
    USER_GOAL_CHANGED = "user_goal_changed"
    ASSUMPTION_INVALIDATED = "assumption_invalidated"
    STEP_BLOCKED = "step_blocked"
    NO_PROGRESS = "no_progress"


class PlanStep(BaseModel):
    id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    dependencies: list[str] = Field(default_factory=list)
    status: PlanStepStatus = PlanStepStatus.PENDING


class Plan(BaseModel):
    objective: str = Field(min_length=1)
    steps: list[PlanStep] = Field(min_length=1)
    revision: int = Field(default=1, ge=1)
    planner_version: str = Field(default="explicit-plan-v1", min_length=1)
    replan_reason: ReplanReason | None = None

    @model_validator(mode="after")
    def validate_graph(self) -> "Plan":
        ids = [step.id for step in self.steps]
        if len(ids) != len(set(ids)):
            raise ValueError("plan step ids must be unique")
        known = set(ids)
        graph: dict[str, list[str]] = {}
        for step in self.steps:
            if step.id in step.dependencies:
                raise ValueError(f"step {step.id} cannot depend on itself")
            unknown = set(step.dependencies) - known
            if unknown:
                raise ValueError(f"step {step.id} has unknown dependencies: {sorted(unknown)}")
            graph[step.id] = list(step.dependencies)

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(step_id: str) -> None:
            if step_id in visited:
                return
            if step_id in visiting:
                raise ValueError("plan dependencies must not contain a cycle")
            visiting.add(step_id)
            for dependency in graph[step_id]:
                visit(dependency)
            visiting.remove(step_id)
            visited.add(step_id)

        for step_id in graph:
            visit(step_id)
        return self

    def ready_step_ids(self) -> list[str]:
        completed = {
            step.id
            for step in self.steps
            if step.status in {PlanStepStatus.COMPLETED, PlanStepStatus.SKIPPED}
        }
        return [
            step.id
            for step in self.steps
            if step.status is PlanStepStatus.PENDING
            and set(step.dependencies).issubset(completed)
        ]

    def completed_fraction(self) -> float:
        done = sum(
            step.status in {PlanStepStatus.COMPLETED, PlanStepStatus.SKIPPED}
            for step in self.steps
        )
        return done / len(self.steps)


class ProgressSignal(BaseModel):
    blocked_step_ids: set[str] = Field(default_factory=set)
    invalidated_step_ids: set[str] = Field(default_factory=set)
    goal_changed: bool = False
    consecutive_no_progress_steps: int = Field(default=0, ge=0)


class ReplanDecision(BaseModel):
    should_replan: bool
    reason: ReplanReason | None = None
    affected_step_ids: set[str] = Field(default_factory=set)


class ReplanPolicy:
    """Application-side trigger policy for deciding when a plan is stale.

    The policy does not invent a replacement plan. It only decides whether the
    current plan has become invalid enough that a planner should be called again.
    """

    def __init__(self, *, no_progress_threshold: int = 2) -> None:
        if no_progress_threshold < 1:
            raise ValueError("no_progress_threshold must be >= 1")
        self.no_progress_threshold = no_progress_threshold

    def evaluate(self, plan: Plan, signal: ProgressSignal) -> ReplanDecision:
        known = {step.id for step in plan.steps}
        blocked = signal.blocked_step_ids & known
        invalidated = signal.invalidated_step_ids & known

        if signal.goal_changed:
            return ReplanDecision(
                should_replan=True,
                reason=ReplanReason.USER_GOAL_CHANGED,
            )
        if invalidated:
            return ReplanDecision(
                should_replan=True,
                reason=ReplanReason.ASSUMPTION_INVALIDATED,
                affected_step_ids=invalidated,
            )
        if blocked:
            return ReplanDecision(
                should_replan=True,
                reason=ReplanReason.STEP_BLOCKED,
                affected_step_ids=blocked,
            )
        if signal.consecutive_no_progress_steps >= self.no_progress_threshold:
            return ReplanDecision(
                should_replan=True,
                reason=ReplanReason.NO_PROGRESS,
            )
        return ReplanDecision(should_replan=False)


def revised_plan(
    previous: Plan,
    *,
    steps: list[PlanStep],
    reason: ReplanReason,
    planner_version: str | None = None,
) -> Plan:
    """Create a new immutable-ish plan revision instead of mutating history."""
    return Plan(
        objective=previous.objective,
        steps=steps,
        revision=previous.revision + 1,
        planner_version=planner_version or previous.planner_version,
        replan_reason=reason,
    )
