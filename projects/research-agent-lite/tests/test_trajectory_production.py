import pytest
from pydantic import ValidationError

from app.agent_control import RunStatus
from app.production import JobKind, ProductionControlPlane, RunJob
from app.trajectory_eval import (
    TrajectoryCase,
    TrajectoryEvaluator,
    TrajectoryPolicy,
    TrajectoryStep,
    TrajectoryStepKind,
)


def test_correct_final_answer_can_still_fail_trajectory_eval() -> None:
    case = TrajectoryCase(
        id="messy-success",
        task_success=True,
        optimal_action_count=2,
        steps=[
            TrajectoryStep(index=1, kind=TrajectoryStepKind.TOOL, action="search", fingerprint="search:q"),
            TrajectoryStep(index=2, kind=TrajectoryStepKind.TOOL, action="search again", necessary=False, fingerprint="search:q"),
            TrajectoryStep(index=3, kind=TrajectoryStepKind.APPROVAL, action="send without approval", correct=False, critical_violation=True),
            TrajectoryStep(index=4, kind=TrajectoryStepKind.FINAL, action="correct final answer"),
        ],
    )
    report = TrajectoryEvaluator().evaluate(case)
    assert report.task_success
    assert report.repeated_action_count == 1
    assert report.approval_violation_count == 1
    assert not report.healthy
    assert "critical policy violation" in " ".join(report.failures)


def test_clean_trajectory_can_pass_with_tool_handoff_and_recovery_metrics() -> None:
    case = TrajectoryCase(
        id="clean",
        task_success=True,
        optimal_action_count=4,
        steps=[
            TrajectoryStep(index=1, kind=TrajectoryStepKind.TOOL, action="search"),
            TrajectoryStep(index=2, kind=TrajectoryStepKind.HANDOFF, action="to retriever"),
            TrajectoryStep(index=3, kind=TrajectoryStepKind.RECOVERY, action="reuse committed"),
            TrajectoryStep(index=4, kind=TrajectoryStepKind.TOOL, action="fetch evidence"),
            TrajectoryStep(index=5, kind=TrajectoryStepKind.FINAL, action="answer"),
        ],
    )
    report = TrajectoryEvaluator().evaluate(case)
    assert report.healthy
    assert report.tool_choice_accuracy == 1.0
    assert report.handoff_accuracy == 1.0
    assert report.recovery_correctness == 1.0
    assert report.loop_efficiency == 1.0


def test_unnecessary_steps_and_bad_handoff_block_even_without_policy_violation() -> None:
    case = TrajectoryCase(
        id="handoff-regression",
        task_success=True,
        optimal_action_count=2,
        steps=[
            TrajectoryStep(index=1, kind=TrajectoryStepKind.HANDOFF, action="wrong specialist", correct=False),
            TrajectoryStep(index=2, kind=TrajectoryStepKind.TOOL, action="search", necessary=False),
            TrajectoryStep(index=3, kind=TrajectoryStepKind.TOOL, action="search2", necessary=False),
            TrajectoryStep(index=4, kind=TrajectoryStepKind.FINAL, action="answer"),
        ],
    )
    report = TrajectoryEvaluator(
        TrajectoryPolicy(maximum_unnecessary_step_rate=0.5, minimum_loop_efficiency=0.6)
    ).evaluate(case)
    assert report.handoff_accuracy == 0.0
    assert not report.healthy


def test_successful_trace_requires_unique_increasing_indexes_and_final_last() -> None:
    with pytest.raises(ValidationError, match="strictly increasing"):
        TrajectoryCase(
            id="bad-order",
            task_success=False,
            optimal_action_count=1,
            steps=[
                TrajectoryStep(index=2, kind=TrajectoryStepKind.TOOL, action="search"),
                TrajectoryStep(index=1, kind=TrajectoryStepKind.TOOL, action="fetch"),
            ],
        )

    with pytest.raises(ValidationError, match="final event must be the last"):
        TrajectoryCase(
            id="early-final",
            task_success=True,
            optimal_action_count=1,
            steps=[
                TrajectoryStep(index=1, kind=TrajectoryStepKind.FINAL, action="answer"),
                TrajectoryStep(index=2, kind=TrajectoryStepKind.TOOL, action="late tool"),
            ],
        )

    with pytest.raises(ValidationError, match="requires a final event"):
        TrajectoryCase(
            id="success-without-final",
            task_success=True,
            optimal_action_count=1,
            steps=[TrajectoryStep(index=1, kind=TrajectoryStepKind.TOOL, action="search")],
        )


def test_critical_violation_on_final_event_still_blocks_health() -> None:
    case = TrajectoryCase(
        id="unsafe-final",
        task_success=True,
        optimal_action_count=1,
        steps=[
            TrajectoryStep(index=1, kind=TrajectoryStepKind.TOOL, action="search"),
            TrajectoryStep(
                index=2,
                kind=TrajectoryStepKind.FINAL,
                action="answer leaks protected data",
                critical_violation=True,
            ),
        ],
    )
    report = TrajectoryEvaluator().evaluate(case)
    assert report.critical_violation_count == 1
    assert not report.healthy


def test_submit_and_claim_use_queued_state_and_revision_to_reject_duplicate_delivery() -> None:
    control = ProductionControlPlane()
    submitted = control.submit(run_id="run-1", tenant_id="tenant-a", objective="research")
    assert submitted.status is RunStatus.QUEUED
    job = control.queue.pop()
    assert job is not None and job.kind is JobKind.START
    assert submitted.revision == job.expected_revision

    first = control.claim(job)
    assert first.accepted
    assert first.record.status is RunStatus.RUNNING

    duplicate = control.claim(job)
    assert not duplicate.accepted
    assert "stale" in duplicate.reason


def test_cancel_before_worker_claim_prevents_execution() -> None:
    control = ProductionControlPlane()
    control.submit(run_id="run-2", tenant_id="tenant-a", objective="research")
    job = control.queue.pop()
    assert job is not None
    cancelled = control.request_cancel("run-2", tenant_id="tenant-a")
    assert cancelled.status is RunStatus.CANCELLED
    assert cancelled.cancel_requested

    claimed = control.claim(job)
    assert not claimed.accepted
    assert "cancelled" in claimed.reason


def test_running_cancel_is_two_phase_until_worker_acknowledges_safe_boundary() -> None:
    control = ProductionControlPlane()
    control.submit(run_id="run-cancel", tenant_id="tenant-a", objective="long tool task")
    start = control.queue.pop()
    assert start is not None
    running = control.claim(start)
    assert running.accepted

    cancelling = control.request_cancel("run-cancel", tenant_id="tenant-a")
    assert cancelling.status is RunStatus.CANCELLING
    assert cancelling.cancel_requested

    with pytest.raises(ValueError, match="only a running run can complete"):
        control.finish(
            "run-cancel",
            tenant_id="tenant-a",
            expected_revision=running.record.revision,
            trace_events=99,
        )

    cancelled = control.acknowledge_cancel(
        "run-cancel",
        tenant_id="tenant-a",
        expected_revision=cancelling.revision,
    )
    assert cancelled.status is RunStatus.CANCELLED


def test_run_store_is_tenant_scoped() -> None:
    control = ProductionControlPlane()
    control.submit(run_id="run-3", tenant_id="tenant-a", objective="private task")
    with pytest.raises(PermissionError):
        control.store.get("run-3", tenant_id="tenant-b")


def test_approval_pause_and_resume_enqueue_exact_run_revision() -> None:
    control = ProductionControlPlane()
    control.submit(run_id="run-4", tenant_id="tenant-a", objective="send report")
    start = control.queue.pop()
    assert start is not None
    running = control.claim(start)
    assert running.accepted

    waiting = control.pause_for_approval(
        "run-4",
        tenant_id="tenant-a",
        expected_revision=running.record.revision,
        approval_request_id="approval:call-9",
        checkpoint_id="run-4:send-9",
    )
    assert waiting.status is RunStatus.WAITING_APPROVAL

    with pytest.raises(ValueError, match="does not match"):
        control.enqueue_resume_after_approval(
            "run-4",
            tenant_id="tenant-a",
            approval_request_id="approval:wrong",
        )

    queued = control.enqueue_resume_after_approval(
        "run-4",
        tenant_id="tenant-a",
        approval_request_id="approval:call-9",
    )
    assert queued.status is RunStatus.QUEUED
    resume = control.queue.pop()
    assert resume is not None and resume.kind is JobKind.RESUME
    assert resume.expected_revision == queued.revision
    assert control.claim(resume).accepted


def test_abandoned_running_run_is_requeued_with_new_revision_and_checkpoint() -> None:
    control = ProductionControlPlane()
    submitted = control.submit(run_id="run-5", tenant_id="tenant-a", objective="long task")
    start = control.queue.pop()
    assert start is not None
    running = control.claim(start)
    assert running.accepted
    assert running.record.status is RunStatus.RUNNING

    abandoned = control.requeue_abandoned(
        "run-5",
        tenant_id="tenant-a",
        expected_revision=running.record.revision,
        checkpoint_id="run-5:checkpoint-7",
        attempt=2,
    )
    assert abandoned.status is RunStatus.QUEUED
    assert abandoned.current_checkpoint_id == "run-5:checkpoint-7"
    assert abandoned.revision > running.record.revision

    recovery = control.queue.pop()
    assert recovery is not None and recovery.kind is JobKind.RESUME
    assert recovery.attempt == 2
    assert recovery.expected_revision == abandoned.revision
    recovered = control.claim(recovery)
    assert recovered.accepted

    old_start = RunJob(
        id="run-5:old-start",
        run_id="run-5",
        tenant_id="tenant-a",
        kind=JobKind.START,
        expected_revision=submitted.revision,
    )
    assert not control.claim(old_start).accepted

    with pytest.raises(RuntimeError, match="stale run revision"):
        control.finish(
            "run-5",
            tenant_id="tenant-a",
            expected_revision=running.record.revision,
            trace_events=99,
        )

    completed = control.finish(
        "run-5",
        tenant_id="tenant-a",
        expected_revision=recovered.record.revision,
        trace_events=12,
    )
    assert completed.status is RunStatus.COMPLETED
    assert completed.trace_events == 12


def test_stale_manual_job_cannot_reanimate_completed_run() -> None:
    control = ProductionControlPlane()
    submitted = control.submit(run_id="run-6", tenant_id="tenant-a", objective="short")
    start = control.queue.pop()
    assert start is not None
    running = control.claim(start)
    assert running.accepted
    completed = control.finish(
        "run-6",
        tenant_id="tenant-a",
        expected_revision=running.record.revision,
        trace_events=7,
    )
    assert completed.status is RunStatus.COMPLETED

    stale = RunJob(
        id="run-6:redelivery",
        run_id="run-6",
        tenant_id="tenant-a",
        kind=JobKind.START,
        expected_revision=submitted.revision,
    )
    claim = control.claim(stale)
    assert not claim.accepted
    assert control.store.get("run-6", tenant_id="tenant-a").status is RunStatus.COMPLETED
