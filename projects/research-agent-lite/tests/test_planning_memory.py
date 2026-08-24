import pytest
from pydantic import ValidationError

from app.memory import (
    MemoryKind,
    MemoryScope,
    MemoryStore,
    MemoryWritePolicy,
    MemoryWriteRequest,
)
from app.planning import (
    Plan,
    PlanStep,
    PlanStepStatus,
    ProgressSignal,
    ReplanPolicy,
    ReplanReason,
    revised_plan,
)


def base_plan() -> Plan:
    return Plan(
        objective="compare papers A and B",
        steps=[
            PlanStep(id="scope", description="define comparison scope", status=PlanStepStatus.COMPLETED),
            PlanStep(id="search", description="find methods", dependencies=["scope"]),
            PlanStep(id="evidence", description="extract evidence", dependencies=["search"]),
            PlanStep(id="synthesize", description="write comparison", dependencies=["evidence"]),
        ],
    )


def test_plan_validates_dependencies_cycles_and_exposes_ready_steps() -> None:
    plan = base_plan()
    assert plan.ready_step_ids() == ["search"]
    assert plan.completed_fraction() == 0.25

    with pytest.raises(ValidationError):
        Plan(
            objective="broken",
            steps=[PlanStep(id="x", description="bad", dependencies=["missing"])],
        )

    with pytest.raises(ValidationError):
        Plan(
            objective="cycle",
            steps=[
                PlanStep(id="a", description="A", dependencies=["b"]),
                PlanStep(id="b", description="B", dependencies=["a"]),
            ],
        )


def test_replan_policy_only_triggers_when_plan_is_stale_enough() -> None:
    policy = ReplanPolicy(no_progress_threshold=2)
    plan = base_plan()

    assert not policy.evaluate(plan, ProgressSignal(consecutive_no_progress_steps=1)).should_replan

    blocked = policy.evaluate(plan, ProgressSignal(blocked_step_ids={"search"}))
    assert blocked.should_replan
    assert blocked.reason is ReplanReason.STEP_BLOCKED
    assert blocked.affected_step_ids == {"search"}

    invalidated = policy.evaluate(plan, ProgressSignal(invalidated_step_ids={"evidence"}))
    assert invalidated.reason is ReplanReason.ASSUMPTION_INVALIDATED

    goal_change = policy.evaluate(plan, ProgressSignal(goal_changed=True))
    assert goal_change.reason is ReplanReason.USER_GOAL_CHANGED

    no_progress = policy.evaluate(plan, ProgressSignal(consecutive_no_progress_steps=2))
    assert no_progress.reason is ReplanReason.NO_PROGRESS


def test_revised_plan_preserves_objective_and_increments_revision() -> None:
    previous = base_plan()
    revised = revised_plan(
        previous,
        reason=ReplanReason.STEP_BLOCKED,
        steps=[
            PlanStep(id="fallback", description="use alternate source"),
            PlanStep(id="synthesize", description="write with caveat", dependencies=["fallback"]),
        ],
    )
    assert revised.objective == previous.objective
    assert revised.revision == 2
    assert revised.replan_reason is ReplanReason.STEP_BLOCKED
    assert previous.revision == 1


def request(**overrides) -> MemoryWriteRequest:
    data = dict(
        id="m1",
        kind=MemoryKind.SEMANTIC,
        scope=MemoryScope.WORKSPACE,
        content="verified paper fact",
        source="paper:p7",
        confidence=0.95,
        reusable=True,
        verified=True,
    )
    data.update(overrides)
    return MemoryWriteRequest(**data)


def test_memory_write_policy_rejects_ephemeral_sensitive_and_unverified_memory() -> None:
    policy = MemoryWritePolicy(minimum_confidence=0.8)

    assert not policy.evaluate(request(kind=MemoryKind.WORKING, scope=MemoryScope.RUN)).allow
    assert not policy.evaluate(request(sensitive=True)).allow
    assert not policy.evaluate(request(verified=False)).allow
    assert not policy.evaluate(request(reusable=False)).allow
    assert not policy.evaluate(request(confidence=0.5)).allow


def test_user_memory_requires_user_scope_and_confirmation() -> None:
    policy = MemoryWritePolicy()
    unconfirmed = request(
        kind=MemoryKind.USER,
        scope=MemoryScope.USER,
        content="用户偏好中文报告",
        source="explicit:user",
        user_confirmed=False,
        verified=False,
    )
    assert not policy.evaluate(unconfirmed).allow

    wrong_scope = unconfirmed.model_copy(update={"user_confirmed": True, "scope": MemoryScope.WORKSPACE})
    assert not policy.evaluate(wrong_scope).allow

    confirmed = unconfirmed.model_copy(update={"user_confirmed": True})
    assert policy.evaluate(confirmed).allow


def test_memory_store_searches_bilingual_content_and_excludes_invalidated_records() -> None:
    store = MemoryStore()
    first = store.write(
        request(
            id="zh",
            content="用户关注滑移铁电器件与畴壁动力学",
            source="verified:project-note",
        )
    )
    second = store.write(
        request(
            id="en",
            content="domain wall depinning threshold in random-field disorder",
            source="verified:paper",
        )
    )
    assert first.record is not None and second.record is not None

    assert [item.id for item in store.search("滑移铁电")] == ["zh"]
    assert [item.id for item in store.search("depinning threshold")] == ["en"]

    store.invalidate("zh", reason="superseded by corrected evidence")
    assert store.get("zh") is not None and not store.get("zh").active
    assert store.search("滑移铁电") == []


def test_memory_store_refuses_to_overwrite_an_existing_id() -> None:
    store = MemoryStore()
    store.write(request(id="stable-id"))
    with pytest.raises(ValueError, match="already exists"):
        store.write(request(id="stable-id", content="silently replacing history would be bad"))
