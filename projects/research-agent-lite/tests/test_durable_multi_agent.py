import asyncio

import pytest
from pydantic import BaseModel, ValidationError

from app.durable import (
    CheckpointStage,
    DurableAction,
    DurableActionRunner,
    RecoveryAction,
    ReplaySafety,
)
from app.multi_agent import (
    AgentDirectory,
    AgentRole,
    AgentSpec,
    HandoffContract,
    HandoffCoordinator,
    HandoffGuard,
    HandoffKind,
    HandoffStatus,
    SupervisorRouter,
    TeamState,
)
from app.tools import Permission, ToolCall, ToolExecutor, ToolRegistry, ToolSpec


class MessageArgs(BaseModel):
    message: str


def make_executor(handler, *, permission: Permission = Permission.READ_ONLY) -> ToolExecutor:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="action",
            description="test action",
            args_model=MessageArgs,
            permission=permission,
        ),
        handler,
    )
    return ToolExecutor(registry)


def durable_action(**overrides) -> DurableAction:
    data = dict(
        run_id="run-1",
        action_id="a1",
        call=ToolCall(id="call-1", name="action", arguments={"message": "hello"}),
        replay_safety=ReplaySafety.SAFE,
    )
    data.update(overrides)
    return DurableAction(**data)


def test_committed_checkpoint_is_reused_without_duplicate_execution() -> None:
    calls = 0

    def handler(message: str):
        nonlocal calls
        calls += 1
        return f"sent:{message}"

    runner = DurableActionRunner(executor=make_executor(handler))
    checkpoint = runner.prepare(durable_action())
    committed = asyncio.run(runner.execute_prepared(checkpoint.id))
    assert committed.stage is CheckpointStage.COMMITTED
    assert calls == 1

    resumed = asyncio.run(runner.resume(checkpoint.id))
    assert resumed.stage is CheckpointStage.COMMITTED
    assert calls == 1


def test_ambiguous_non_idempotent_in_flight_action_requires_reconciliation() -> None:
    calls = 0

    def handler(message: str):
        nonlocal calls
        calls += 1
        return message

    runner = DurableActionRunner(
        executor=make_executor(handler, permission=Permission.SIDE_EFFECT)
    )
    checkpoint = runner.prepare(
        durable_action(replay_safety=ReplaySafety.NON_IDEMPOTENT)
    )
    runner.begin(checkpoint.id)  # process may crash after an external effect but before commit

    decision = runner.recovery_decision(checkpoint.id)
    assert decision.action is RecoveryAction.RECONCILE
    with pytest.raises(RuntimeError, match="requires reconcile"):
        asyncio.run(runner.resume(checkpoint.id, approved=True))
    assert calls == 0


def test_safe_in_flight_action_can_be_replayed_after_crash() -> None:
    calls = 0

    def handler(message: str):
        nonlocal calls
        calls += 1
        return message.upper()

    runner = DurableActionRunner(executor=make_executor(handler))
    checkpoint = runner.prepare(durable_action(replay_safety=ReplaySafety.SAFE))
    runner.begin(checkpoint.id)

    decision = runner.recovery_decision(checkpoint.id)
    assert decision.action is RecoveryAction.RETRY
    resumed = asyncio.run(runner.resume(checkpoint.id))
    assert resumed.stage is CheckpointStage.COMMITTED
    assert calls == 1
    assert [item.stage for item in runner.store.history(checkpoint.id)] == [
        CheckpointStage.PREPARED,
        CheckpointStage.IN_FLIGHT,
        CheckpointStage.PREPARED,
        CheckpointStage.IN_FLIGHT,
        CheckpointStage.COMMITTED,
    ]


def test_external_idempotency_contract_requires_a_key() -> None:
    with pytest.raises(ValidationError):
        durable_action(
            replay_safety=ReplaySafety.EXTERNAL_IDEMPOTENT,
            idempotency_key=None,
        )


def test_retryable_recorded_failure_can_resume_and_then_commit() -> None:
    calls = 0

    def flaky(message: str):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError("temporary timeout")
        return message

    runner = DurableActionRunner(executor=make_executor(flaky))
    checkpoint = runner.prepare(durable_action())
    failed = asyncio.run(runner.execute_prepared(checkpoint.id))
    assert failed.stage is CheckpointStage.FAILED
    assert runner.recovery_decision(checkpoint.id).action is RecoveryAction.RETRY

    recovered = asyncio.run(runner.resume(checkpoint.id))
    assert recovered.stage is CheckpointStage.COMMITTED
    assert calls == 2


def directory() -> AgentDirectory:
    result = AgentDirectory()
    result.register(
        AgentSpec(
            id="supervisor",
            role=AgentRole.SUPERVISOR,
            capabilities={"route", "retrieve", "write"},
        )
    )
    result.register(
        AgentSpec(id="retriever", role=AgentRole.SPECIALIST, capabilities={"retrieve"})
    )
    result.register(
        AgentSpec(id="writer", role=AgentRole.SPECIALIST, capabilities={"write"})
    )
    result.register(
        AgentSpec(
            id="researcher",
            role=AgentRole.SPECIALIST,
            capabilities={"retrieve", "write"},
        )
    )
    return result


def test_supervisor_router_prefers_least_privileged_capable_specialist() -> None:
    chosen = SupervisorRouter(directory()).choose({"retrieve"})
    assert chosen.id == "retriever"


def test_typed_handoff_changes_owner_and_completion_returns_to_supervisor() -> None:
    state = TeamState(owner_agent="supervisor")
    coordinator = HandoffCoordinator(directory=directory())
    contract = HandoffContract(
        id="h1",
        from_agent="supervisor",
        to_agent="retriever",
        objective="find evidence for the comparison",
        required_capabilities={"retrieve"},
        context_refs=["query:q1", "plan:p3"],
        expected_output="evidence ids with provenance",
        return_to="supervisor",
    )

    decision = coordinator.submit(state, contract)
    assert decision.allow
    assert decision.record is not None and decision.record.status is HandoffStatus.ACCEPTED
    assert state.owner_agent == "retriever"

    completed = coordinator.complete(state, "h1", result_ref="artifact:evidence-pack-17")
    assert completed.status is HandoffStatus.COMPLETED
    assert completed.result_ref == "artifact:evidence-pack-17"
    assert state.owner_agent == "supervisor"


def test_handoff_rejects_capability_mismatch_and_non_owner_delegation() -> None:
    state = TeamState(owner_agent="supervisor")
    coordinator = HandoffCoordinator(directory=directory())
    mismatch = HandoffContract(
        id="bad-cap",
        from_agent="supervisor",
        to_agent="writer",
        objective="retrieve papers",
        required_capabilities={"retrieve"},
        expected_output="paper ids",
        return_to="supervisor",
    )
    assert not coordinator.submit(state, mismatch).allow
    assert state.owner_agent == "supervisor"

    non_owner = HandoffContract(
        id="bad-owner",
        from_agent="writer",
        to_agent="retriever",
        objective="retrieve papers",
        required_capabilities={"retrieve"},
        expected_output="paper ids",
        return_to="writer",
    )
    assert not coordinator.submit(state, non_owner).allow


def test_guard_blocks_circular_delegation_and_delegation_budget() -> None:
    state = TeamState(owner_agent="supervisor")
    coordinator = HandoffCoordinator(directory=directory(), guard=HandoffGuard(max_delegations=3))

    first = HandoffContract(
        id="h1",
        from_agent="supervisor",
        to_agent="researcher",
        objective="research",
        required_capabilities={"retrieve"},
        expected_output="research bundle",
        return_to="supervisor",
    )
    assert coordinator.submit(state, first).allow

    second = HandoffContract(
        id="h2",
        from_agent="researcher",
        to_agent="writer",
        objective="draft",
        required_capabilities={"write"},
        expected_output="draft",
        return_to="researcher",
    )
    assert coordinator.submit(state, second).allow

    circular = HandoffContract(
        id="h3",
        from_agent="writer",
        to_agent="researcher",
        objective="please research again",
        required_capabilities={"retrieve"},
        expected_output="more research",
        return_to="writer",
    )
    rejected = coordinator.submit(state, circular)
    assert not rejected.allow
    assert "circular" in rejected.reason
