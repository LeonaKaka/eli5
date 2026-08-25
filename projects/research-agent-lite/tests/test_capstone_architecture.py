from dataclasses import replace

from app.capstone_architecture import (
    ArchitectureComponent,
    ArchitectureConcern,
    CapstoneArchitectureReviewer,
    FailureScenario,
    failure_drill,
    reference_design,
)


def test_v70_reference_design_has_explicit_owner_for_every_capstone_concern() -> None:
    design = reference_design()
    review = CapstoneArchitectureReviewer().review(design)

    assert review.accepted is True
    assert review.violations == ()
    assert set(design.owners) == set(ArchitectureConcern)


def test_v70_checkpoint_queue_llm_and_event_stream_cannot_take_over_product_ownership() -> None:
    design = reference_design()
    broken = dict(design.owners)
    broken[ArchitectureConcern.RUN_TRUTH] = ArchitectureComponent.LANGGRAPH_CHECKPOINTER
    broken[ArchitectureConcern.EXECUTION_OWNERSHIP] = ArchitectureComponent.QUEUE
    broken[ArchitectureConcern.TOOL_AUTHORITY] = ArchitectureComponent.LLM
    broken[ArchitectureConcern.CLIENT_EVENTS] = ArchitectureComponent.RUN_STORE

    review = CapstoneArchitectureReviewer().review(replace(design, owners=broken))

    assert review.accepted is False
    message = "\n".join(review.violations)
    assert "run_truth must be owned by run_store" in message
    assert "execution_ownership must be owned by lease_coordinator" in message
    assert "tool_authority must be owned by security_policy" in message
    assert "client_events must be owned by event_store" in message


def test_v70_cross_cutting_invariants_cannot_be_removed_by_a_pretty_architecture_diagram() -> None:
    design = replace(
        reference_design(),
        tenant_scoped_run_keys=False,
        run_revision_cas=False,
        lease_fencing=False,
        exact_action_approval=False,
        sandbox_process_isolation=False,
        admission_control=False,
    )

    review = CapstoneArchitectureReviewer().review(design)

    assert review.accepted is False
    message = "\n".join(review.violations)
    assert "tenant scoped" in message
    assert "revision/CAS" in message
    assert "lease/fencing" in message
    assert "exact proposed action" in message
    assert "real isolation boundary" in message
    assert "admission/backpressure" in message


def test_v70_worker_crash_drill_requires_checkpoint_plus_new_ownership_and_fencing() -> None:
    drill = failure_drill(FailureScenario.WORKER_CRASH)

    assert any("heartbeat expires" in step for step in drill.detect)
    assert any("fencing rejects zombie writes" in step for step in drill.contain)
    assert any("latest checkpoint" in step for step in drill.recover)
    assert any("higher fencing token" in step for step in drill.recover)


def test_v70_malicious_content_drill_keeps_authority_outside_the_model() -> None:
    drill = failure_drill(FailureScenario.MALICIOUS_WEB_CONTENT)

    assert any("external_untrusted" in step for step in drill.detect)
    assert any("cannot be expanded by prompt text" in step for step in drill.contain)
    assert "cannot grant capability" in drill.invariant


def test_v70_sse_disconnect_recovers_projection_without_redefining_run_truth() -> None:
    drill = failure_drill(FailureScenario.SSE_DISCONNECT)

    assert any("do not cancel" in step for step in drill.contain)
    assert any("Last-Event-ID" in step for step in drill.recover)
    assert any("GET Run truth" in step for step in drill.recover)
    assert "not the source of Run truth" in drill.invariant


def test_v70_ambiguous_external_effect_never_blindly_retries_non_idempotent_work() -> None:
    drill = failure_drill(FailureScenario.AMBIGUOUS_SIDE_EFFECT)

    assert any("do not blindly replay" in step for step in drill.contain)
    assert any("reconcile external reality" in step for step in drill.recover)
    assert "never claims universal exactly-once" in drill.invariant


def test_v70_run_store_outage_and_overload_fail_safe_instead_of_inventing_state() -> None:
    store_drill = failure_drill(FailureScenario.RUN_STORE_UNAVAILABLE)
    overload_drill = failure_drill(FailureScenario.OVERLOAD)

    assert any("readiness becomes unhealthy" in step for step in store_drill.contain)
    assert "must not invent state" in store_drill.invariant
    assert any("reject or defer new work" in step for step in overload_drill.contain)
    assert "bounded overload" in overload_drill.invariant
