from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json


class DistributedRuntimeError(RuntimeError):
    pass


class BackpressureError(DistributedRuntimeError):
    def __init__(self, message: str, *, retry_after_seconds: int = 5) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class RunPhase(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class WorkerMode(StrEnum):
    ACTIVE = "active"
    DRAINING = "draining"


@dataclass(frozen=True)
class QueueDelivery:
    delivery_id: str
    run_id: str
    tenant_id: str
    attempt: int
    checkpoint_id: str | None = None


@dataclass(frozen=True)
class LeaseGrant:
    run_id: str
    tenant_id: str
    worker_id: str
    fencing_token: int
    attempt: int
    expires_at: float


@dataclass
class RunSlot:
    run_id: str
    tenant_id: str
    phase: RunPhase = RunPhase.QUEUED
    latest_attempt: int = 1
    checkpoint_id: str | None = None
    lease: LeaseGrant | None = None


@dataclass(frozen=True)
class ClaimDecision:
    accepted: bool
    reason: str
    lease: LeaseGrant | None = None


@dataclass(frozen=True)
class EffectResult:
    applied: bool
    replayed: bool
    value: str
    fencing_token: int


@dataclass(frozen=True)
class AdmissionPolicy:
    max_queue_depth: int = 100
    max_inflight_per_tenant: int = 10
    retry_after_seconds: int = 5


class FencedEffectLedger:
    """Teaching downstream store with idempotency + fencing checks.

    This models a shared system that actually understands fencing tokens. Many
    external APIs do not. For those systems, the caller still needs the durable
    action replay/idempotency/reconciliation rules from the earlier Agent course.
    """

    def __init__(self) -> None:
        self._highest_fence: dict[str, int] = {}
        self._idempotency: dict[tuple[str, str], tuple[str, str, int]] = {}

    @staticmethod
    def _fingerprint(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def apply(
        self,
        *,
        resource_id: str,
        fencing_token: int,
        idempotency_key: str,
        value: str,
    ) -> EffectResult:
        key = (resource_id, idempotency_key)
        fingerprint = self._fingerprint(value)
        if key in self._idempotency:
            prior_fingerprint, prior_value, prior_fence = self._idempotency[key]
            if prior_fingerprint != fingerprint:
                raise DistributedRuntimeError(
                    "idempotency key was reused with a different effect payload"
                )
            return EffectResult(
                applied=False,
                replayed=True,
                value=prior_value,
                fencing_token=prior_fence,
            )

        highest = self._highest_fence.get(resource_id, 0)
        if fencing_token < highest:
            raise DistributedRuntimeError(
                f"stale fencing token: {fencing_token} < current {highest}"
            )

        self._highest_fence[resource_id] = fencing_token
        self._idempotency[key] = (fingerprint, value, fencing_token)
        return EffectResult(
            applied=True,
            replayed=False,
            value=value,
            fencing_token=fencing_token,
        )


class DistributedRunCoordinator:
    """Deterministic multi-worker teaching coordinator.

    Queue delivery is intentionally at-least-once. A delivery does not own the
    Run. `claim()` creates a time-bounded lease and monotonically increasing
    fencing token. Every worker-side mutation must present that exact lease.

    Heartbeats extend ownership. Expired leases are reaped and requeued from the
    latest checkpoint. A worker in DRAINING mode may heartbeat/finish existing
    work but cannot claim new deliveries.
    """

    def __init__(
        self,
        *,
        lease_ttl_seconds: float = 30.0,
        admission: AdmissionPolicy | None = None,
    ) -> None:
        if lease_ttl_seconds <= 0:
            raise ValueError("lease_ttl_seconds must be positive")
        self.lease_ttl_seconds = lease_ttl_seconds
        self.admission = admission or AdmissionPolicy()
        self._runs: dict[str, RunSlot] = {}
        self._queue: deque[QueueDelivery] = deque()
        self._next_fence: dict[str, int] = {}
        self._worker_modes: dict[str, WorkerMode] = {}

    def register_worker(self, worker_id: str) -> None:
        if not worker_id.strip():
            raise ValueError("worker_id is required")
        self._worker_modes.setdefault(worker_id, WorkerMode.ACTIVE)

    def start_draining(self, worker_id: str) -> None:
        self.register_worker(worker_id)
        self._worker_modes[worker_id] = WorkerMode.DRAINING

    def worker_mode(self, worker_id: str) -> WorkerMode:
        return self._worker_modes.get(worker_id, WorkerMode.ACTIVE)

    def submit(self, *, run_id: str, tenant_id: str) -> RunSlot:
        if run_id in self._runs:
            raise ValueError(f"run already exists: {run_id}")
        if len(self._queue) >= self.admission.max_queue_depth:
            raise BackpressureError(
                "global queue depth exceeds admission policy",
                retry_after_seconds=self.admission.retry_after_seconds,
            )
        if self._tenant_inflight(tenant_id) >= self.admission.max_inflight_per_tenant:
            raise BackpressureError(
                "tenant already has too many queued/running runs",
                retry_after_seconds=self.admission.retry_after_seconds,
            )

        slot = RunSlot(run_id=run_id, tenant_id=tenant_id)
        self._runs[run_id] = slot
        self._queue.append(
            QueueDelivery(
                delivery_id=f"{run_id}:a1:d1",
                run_id=run_id,
                tenant_id=tenant_id,
                attempt=1,
            )
        )
        return self.snapshot(run_id)

    def snapshot(self, run_id: str) -> RunSlot:
        try:
            slot = self._runs[run_id]
        except KeyError as exc:
            raise KeyError(f"unknown run: {run_id}") from exc
        return RunSlot(
            run_id=slot.run_id,
            tenant_id=slot.tenant_id,
            phase=slot.phase,
            latest_attempt=slot.latest_attempt,
            checkpoint_id=slot.checkpoint_id,
            lease=slot.lease,
        )

    def pop_delivery(self) -> QueueDelivery | None:
        if not self._queue:
            return None
        return self._queue.popleft()

    def inject_redelivery(self, delivery: QueueDelivery, *, suffix: str = "dup") -> None:
        """Model an at-least-once queue delivering the same logical attempt again."""
        self._queue.append(
            QueueDelivery(
                delivery_id=f"{delivery.delivery_id}:{suffix}",
                run_id=delivery.run_id,
                tenant_id=delivery.tenant_id,
                attempt=delivery.attempt,
                checkpoint_id=delivery.checkpoint_id,
            )
        )

    def claim(
        self,
        delivery: QueueDelivery,
        *,
        worker_id: str,
        now: float,
    ) -> ClaimDecision:
        self.register_worker(worker_id)
        if self.worker_mode(worker_id) is WorkerMode.DRAINING:
            return ClaimDecision(False, "worker is draining and cannot claim new work")

        slot = self._runs.get(delivery.run_id)
        if slot is None or slot.tenant_id != delivery.tenant_id:
            return ClaimDecision(False, "delivery does not match a known tenant-scoped run")
        if slot.phase in {RunPhase.COMPLETED, RunPhase.CANCELLED}:
            return ClaimDecision(False, f"run is terminal: {slot.phase.value}")
        if delivery.attempt != slot.latest_attempt:
            return ClaimDecision(False, "stale or duplicate delivery attempt")
        if slot.lease is not None:
            if slot.lease.expires_at <= now:
                return ClaimDecision(False, "lease expired; watchdog must reap before recovery")
            return ClaimDecision(False, "another worker already holds the active lease")
        if slot.phase is not RunPhase.QUEUED:
            return ClaimDecision(False, f"run is not claimable from {slot.phase.value}")

        fence = self._next_fence.get(slot.run_id, 0) + 1
        self._next_fence[slot.run_id] = fence
        lease = LeaseGrant(
            run_id=slot.run_id,
            tenant_id=slot.tenant_id,
            worker_id=worker_id,
            fencing_token=fence,
            attempt=delivery.attempt,
            expires_at=now + self.lease_ttl_seconds,
        )
        slot.lease = lease
        slot.phase = RunPhase.RUNNING
        return ClaimDecision(True, "worker acquired lease and fencing token", lease)

    def heartbeat(self, lease: LeaseGrant, *, now: float) -> LeaseGrant:
        slot = self._validate_live_lease(lease, now=now)
        renewed = LeaseGrant(
            run_id=lease.run_id,
            tenant_id=lease.tenant_id,
            worker_id=lease.worker_id,
            fencing_token=lease.fencing_token,
            attempt=lease.attempt,
            expires_at=now + self.lease_ttl_seconds,
        )
        slot.lease = renewed
        return renewed

    def checkpoint(self, lease: LeaseGrant, *, checkpoint_id: str, now: float) -> RunSlot:
        if not checkpoint_id.strip():
            raise ValueError("checkpoint_id is required")
        slot = self._validate_live_lease(lease, now=now)
        slot.checkpoint_id = checkpoint_id
        return self.snapshot(slot.run_id)

    def complete(self, lease: LeaseGrant, *, now: float) -> RunSlot:
        slot = self._validate_live_lease(lease, now=now)
        slot.phase = RunPhase.COMPLETED
        slot.lease = None
        return self.snapshot(slot.run_id)

    def reap_expired(self, *, now: float) -> list[QueueDelivery]:
        recovered: list[QueueDelivery] = []
        for slot in self._runs.values():
            lease = slot.lease
            if slot.phase is not RunPhase.RUNNING or lease is None or lease.expires_at > now:
                continue
            slot.lease = None
            slot.phase = RunPhase.QUEUED
            slot.latest_attempt += 1
            delivery = QueueDelivery(
                delivery_id=f"{slot.run_id}:a{slot.latest_attempt}:recovery",
                run_id=slot.run_id,
                tenant_id=slot.tenant_id,
                attempt=slot.latest_attempt,
                checkpoint_id=slot.checkpoint_id,
            )
            self._queue.append(delivery)
            recovered.append(delivery)
        return recovered

    def _validate_live_lease(self, lease: LeaseGrant, *, now: float) -> RunSlot:
        slot = self._runs.get(lease.run_id)
        if slot is None or slot.tenant_id != lease.tenant_id:
            raise DistributedRuntimeError("lease does not belong to a known tenant-scoped run")
        current = slot.lease
        if current is None:
            raise DistributedRuntimeError("run no longer has an active lease")
        if current.fencing_token != lease.fencing_token or current.worker_id != lease.worker_id:
            raise DistributedRuntimeError("stale worker lease/fencing token")
        if current.expires_at <= now:
            raise DistributedRuntimeError("worker lease has expired")
        if slot.phase is not RunPhase.RUNNING:
            raise DistributedRuntimeError("lease is not attached to a running run")
        return slot

    def _tenant_inflight(self, tenant_id: str) -> int:
        return sum(
            1
            for slot in self._runs.values()
            if slot.tenant_id == tenant_id and slot.phase in {RunPhase.QUEUED, RunPhase.RUNNING}
        )

    @property
    def queue_depth(self) -> int:
        return len(self._queue)


def effect_payload_fingerprint(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
