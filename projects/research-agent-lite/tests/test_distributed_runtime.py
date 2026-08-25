import pytest

from app.distributed_runtime import (
    AdmissionPolicy,
    BackpressureError,
    DistributedRunCoordinator,
    DistributedRuntimeError,
    FencedEffectLedger,
    RunPhase,
    WorkerMode,
)


def test_v66_at_least_once_redelivery_does_not_create_two_active_owners() -> None:
    coordinator = DistributedRunCoordinator(lease_ttl_seconds=10)
    coordinator.submit(run_id="run-1", tenant_id="tenant-a")
    first = coordinator.pop_delivery()
    assert first is not None
    coordinator.inject_redelivery(first)

    claimed = coordinator.claim(first, worker_id="worker-a", now=0)
    duplicate = coordinator.pop_delivery()
    assert duplicate is not None
    rejected = coordinator.claim(duplicate, worker_id="worker-b", now=1)

    assert claimed.accepted is True
    assert claimed.lease is not None
    assert rejected.accepted is False
    assert "active lease" in rejected.reason
    assert coordinator.snapshot("run-1").lease.worker_id == "worker-a"


def test_v66_expired_worker_is_requeued_from_checkpoint_and_new_worker_gets_higher_fence() -> None:
    coordinator = DistributedRunCoordinator(lease_ttl_seconds=10)
    coordinator.submit(run_id="run-2", tenant_id="tenant-a")
    delivery = coordinator.pop_delivery()
    assert delivery is not None

    first = coordinator.claim(delivery, worker_id="worker-a", now=0)
    assert first.lease is not None
    lease_a = first.lease
    coordinator.checkpoint(lease_a, checkpoint_id="checkpoint-7", now=5)

    recovered = coordinator.reap_expired(now=11)
    assert len(recovered) == 1
    assert recovered[0].attempt == 2
    assert recovered[0].checkpoint_id == "checkpoint-7"

    retry = coordinator.pop_delivery()
    assert retry is not None
    second = coordinator.claim(retry, worker_id="worker-b", now=11)
    assert second.accepted is True
    assert second.lease is not None
    assert second.lease.fencing_token == lease_a.fencing_token + 1

    with pytest.raises(DistributedRuntimeError, match="stale worker lease|no longer has"):
        coordinator.complete(lease_a, now=11.5)

    completed = coordinator.complete(second.lease, now=12)
    assert completed.phase is RunPhase.COMPLETED


def test_v66_heartbeat_extends_lease_but_cannot_revive_an_already_expired_owner() -> None:
    coordinator = DistributedRunCoordinator(lease_ttl_seconds=10)
    coordinator.submit(run_id="run-3", tenant_id="tenant-a")
    delivery = coordinator.pop_delivery()
    assert delivery is not None
    claim = coordinator.claim(delivery, worker_id="worker-a", now=0)
    assert claim.lease is not None

    renewed = coordinator.heartbeat(claim.lease, now=8)
    assert renewed.expires_at == 18
    assert coordinator.reap_expired(now=11) == []

    with pytest.raises(DistributedRuntimeError, match="expired"):
        coordinator.heartbeat(renewed, now=18)


def test_v66_fenced_effect_store_rejects_stale_worker_and_replays_same_idempotency_key() -> None:
    ledger = FencedEffectLedger()

    current = ledger.apply(
        resource_id="report:42",
        fencing_token=42,
        idempotency_key="publish-report-42",
        value="version-b",
    )
    replay = ledger.apply(
        resource_id="report:42",
        fencing_token=42,
        idempotency_key="publish-report-42",
        value="version-b",
    )

    assert current.applied is True
    assert replay.replayed is True
    assert replay.value == "version-b"

    with pytest.raises(DistributedRuntimeError, match="stale fencing token"):
        ledger.apply(
            resource_id="report:42",
            fencing_token=41,
            idempotency_key="late-worker-a",
            value="stale-version-a",
        )

    with pytest.raises(DistributedRuntimeError, match="different effect payload"):
        ledger.apply(
            resource_id="report:42",
            fencing_token=42,
            idempotency_key="publish-report-42",
            value="changed-payload",
        )


def test_v66_admission_control_applies_backpressure_before_unbounded_queue_growth() -> None:
    coordinator = DistributedRunCoordinator(
        admission=AdmissionPolicy(
            max_queue_depth=10,
            max_inflight_per_tenant=2,
            retry_after_seconds=7,
        )
    )
    coordinator.submit(run_id="run-a", tenant_id="tenant-a")
    coordinator.submit(run_id="run-b", tenant_id="tenant-a")

    with pytest.raises(BackpressureError) as exc_info:
        coordinator.submit(run_id="run-c", tenant_id="tenant-a")

    assert exc_info.value.retry_after_seconds == 7
    assert "tenant" in str(exc_info.value)


def test_v66_graceful_drain_stops_new_claims_but_existing_lease_can_finish() -> None:
    coordinator = DistributedRunCoordinator(lease_ttl_seconds=20)
    coordinator.register_worker("worker-a")
    coordinator.submit(run_id="run-active", tenant_id="tenant-a")
    first_delivery = coordinator.pop_delivery()
    assert first_delivery is not None
    first = coordinator.claim(first_delivery, worker_id="worker-a", now=0)
    assert first.lease is not None

    coordinator.start_draining("worker-a")
    assert coordinator.worker_mode("worker-a") is WorkerMode.DRAINING

    coordinator.submit(run_id="run-next", tenant_id="tenant-b")
    next_delivery = coordinator.pop_delivery()
    assert next_delivery is not None
    rejected = coordinator.claim(next_delivery, worker_id="worker-a", now=1)
    assert rejected.accepted is False
    assert "draining" in rejected.reason

    renewed = coordinator.heartbeat(first.lease, now=2)
    finished = coordinator.complete(renewed, now=3)
    assert finished.phase is RunPhase.COMPLETED
