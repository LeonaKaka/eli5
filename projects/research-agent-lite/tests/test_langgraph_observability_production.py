import pytest

from app.agent_control import RunStatus
from app.langgraph_observability import CallBudgetMiddleware, collect_stream_trace
from app.langgraph_production import ProductionGraphBridge


def test_v49_middleware_blocks_after_model_call_budget_without_touching_business_nodes() -> None:
    middleware = CallBudgetMiddleware(max_model_calls=2)

    assert middleware.before_model(
        {"messages": [], "model_call_count": 0},
        None,
    ) is None

    after = middleware.after_model(
        {"messages": [], "model_call_count": 1},
        None,
    )
    assert after == {"model_call_count": 2, "blocked_by_budget": False}

    blocked = middleware.before_model(
        {"messages": [], "model_call_count": 2},
        None,
    )
    assert blocked is not None
    assert blocked["jump_to"] == "end"
    assert blocked["blocked_by_budget"] is True


def test_v49_v2_stream_separates_updates_values_and_custom_progress() -> None:
    parts = collect_stream_trace("depinning")
    types = [part["type"] for part in parts]

    assert "updates" in types
    assert "values" in types
    assert "custom" in types

    custom = [part["data"] for part in parts if part["type"] == "custom"]
    assert [item["phase"] for item in custom] == ["retrieve", "synthesize"]
    assert custom[0]["progress"] == 35
    assert custom[1]["progress"] == 85

    updates = [part["data"] for part in parts if part["type"] == "updates"]
    assert any("retrieve" in update for update in updates)
    assert any("synthesize" in update for update in updates)


def test_v50_direct_run_keeps_product_revision_control_while_graph_owns_thread_state() -> None:
    bridge = ProductionGraphBridge()
    submitted = bridge.submit(
        run_id="run-direct",
        tenant_id="tenant-a",
        objective="compare papers",
        approval_required=False,
    )
    assert submitted.status is RunStatus.QUEUED

    job = bridge.control.queue.pop()
    assert job is not None
    outcome = bridge.execute_job(job)

    assert outcome.run.status is RunStatus.COMPLETED
    assert not outcome.interrupted
    assert outcome.graph_result["result"] == "completed:compare papers"
    assert outcome.run.revision > submitted.revision
    assert outcome.thread_id == "tenant:tenant-a:run:run-direct"


def test_v50_interrupt_checkpoint_is_written_back_to_product_run_before_approval() -> None:
    bridge = ProductionGraphBridge()
    bridge.submit(
        run_id="run-approval",
        tenant_id="tenant-a",
        objective="send report",
        approval_required=True,
    )
    start = bridge.control.queue.pop()
    assert start is not None

    paused = bridge.execute_job(start)
    assert paused.interrupted
    assert paused.run.status is RunStatus.WAITING_APPROVAL
    assert paused.run.current_checkpoint_id
    assert paused.run.approval_request_id

    snapshot = bridge.get_graph_state("run-approval", tenant_id="tenant-a")
    assert snapshot.config["configurable"]["checkpoint_id"] == paused.run.current_checkpoint_id


def test_v50_only_authorized_matching_approval_can_enqueue_graph_resume() -> None:
    bridge = ProductionGraphBridge()
    bridge.submit(
        run_id="run-resume",
        tenant_id="tenant-a",
        objective="send report",
        approval_required=True,
    )
    start = bridge.control.queue.pop()
    paused = bridge.execute_job(start)
    request_id = paused.run.approval_request_id
    assert request_id is not None

    with pytest.raises(PermissionError):
        bridge.resolve_approval(
            "run-resume",
            tenant_id="tenant-a",
            approval_request_id=request_id,
            approved=True,
            actor_authorized=False,
        )

    with pytest.raises(ValueError, match="does not match"):
        bridge.resolve_approval(
            "run-resume",
            tenant_id="tenant-a",
            approval_request_id="approval:wrong",
            approved=True,
            actor_authorized=True,
        )

    queued = bridge.resolve_approval(
        "run-resume",
        tenant_id="tenant-a",
        approval_request_id=request_id,
        approved=True,
        actor_authorized=True,
    )
    assert queued.status is RunStatus.QUEUED

    resume = bridge.control.queue.pop()
    assert resume is not None
    completed = bridge.execute_job(resume)
    assert completed.run.status is RunStatus.COMPLETED
    assert completed.graph_result["result"] == "completed:send report"


def test_v50_rejected_approval_cancels_product_run_without_resuming_graph() -> None:
    bridge = ProductionGraphBridge()
    bridge.submit(
        run_id="run-reject",
        tenant_id="tenant-a",
        objective="send report",
        approval_required=True,
    )
    start = bridge.control.queue.pop()
    paused = bridge.execute_job(start)

    cancelled = bridge.resolve_approval(
        "run-reject",
        tenant_id="tenant-a",
        approval_request_id=paused.run.approval_request_id,
        approved=False,
        actor_authorized=True,
    )
    assert cancelled.status is RunStatus.CANCELLED
    assert len(bridge.control.queue) == 0


def test_v50_graph_state_inspection_is_tenant_scoped_by_product_control_plane() -> None:
    bridge = ProductionGraphBridge()
    bridge.submit(
        run_id="private-run",
        tenant_id="tenant-a",
        objective="private research",
    )
    job = bridge.control.queue.pop()
    bridge.execute_job(job)

    with pytest.raises(PermissionError):
        bridge.get_graph_state("private-run", tenant_id="tenant-b")
