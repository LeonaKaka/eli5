from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ArchitectureConcern(StrEnum):
    IDENTITY = "identity"
    RUN_TRUTH = "run_truth"
    DELIVERY = "delivery"
    EXECUTION_OWNERSHIP = "execution_ownership"
    GRAPH_CONTINUATION = "graph_continuation"
    TOOL_AUTHORITY = "tool_authority"
    CODE_ISOLATION = "code_isolation"
    ARTIFACT_STORAGE = "artifact_storage"
    CLIENT_EVENTS = "client_events"
    OPERATIONAL_TELEMETRY = "operational_telemetry"
    QUALITY_TRUTH = "quality_truth"
    SIDE_EFFECT_SAFETY = "side_effect_safety"


class ArchitectureComponent(StrEnum):
    IDENTITY_PROVIDER = "identity_provider"
    FASTAPI = "fastapi"
    RUN_STORE = "run_store"
    QUEUE = "queue"
    LEASE_COORDINATOR = "lease_coordinator"
    LANGGRAPH_CHECKPOINTER = "langgraph_checkpointer"
    SECURITY_POLICY = "security_policy"
    SANDBOX = "sandbox"
    OBJECT_STORE = "object_store"
    EVENT_STORE = "event_store"
    OBSERVABILITY_PIPELINE = "observability_pipeline"
    EVAL_PIPELINE = "eval_pipeline"
    IDEMPOTENCY_RECONCILIATION = "idempotency_reconciliation"
    LLM = "llm"


REFERENCE_OWNERS: dict[ArchitectureConcern, ArchitectureComponent] = {
    ArchitectureConcern.IDENTITY: ArchitectureComponent.IDENTITY_PROVIDER,
    ArchitectureConcern.RUN_TRUTH: ArchitectureComponent.RUN_STORE,
    ArchitectureConcern.DELIVERY: ArchitectureComponent.QUEUE,
    ArchitectureConcern.EXECUTION_OWNERSHIP: ArchitectureComponent.LEASE_COORDINATOR,
    ArchitectureConcern.GRAPH_CONTINUATION: ArchitectureComponent.LANGGRAPH_CHECKPOINTER,
    ArchitectureConcern.TOOL_AUTHORITY: ArchitectureComponent.SECURITY_POLICY,
    ArchitectureConcern.CODE_ISOLATION: ArchitectureComponent.SANDBOX,
    ArchitectureConcern.ARTIFACT_STORAGE: ArchitectureComponent.OBJECT_STORE,
    ArchitectureConcern.CLIENT_EVENTS: ArchitectureComponent.EVENT_STORE,
    ArchitectureConcern.OPERATIONAL_TELEMETRY: ArchitectureComponent.OBSERVABILITY_PIPELINE,
    ArchitectureConcern.QUALITY_TRUTH: ArchitectureComponent.EVAL_PIPELINE,
    ArchitectureConcern.SIDE_EFFECT_SAFETY: ArchitectureComponent.IDEMPOTENCY_RECONCILIATION,
}


@dataclass(frozen=True)
class CapacityEnvelope:
    concurrent_users: int = 1_000
    maximum_run_hours: int = 6
    api_replicas: int = 2
    worker_replicas: int = 8
    global_queue_limit: int = 5_000
    per_tenant_inflight_limit: int = 10

    def violations(self) -> tuple[str, ...]:
        problems: list[str] = []
        if self.concurrent_users <= 0:
            problems.append("concurrent_users must be positive")
        if self.maximum_run_hours <= 0:
            problems.append("maximum_run_hours must be positive")
        if self.api_replicas <= 0:
            problems.append("at least one API replica is required")
        if self.worker_replicas <= 0:
            problems.append("at least one Worker replica is required")
        if self.global_queue_limit <= 0:
            problems.append("global queue admission limit must be finite and positive")
        if self.per_tenant_inflight_limit <= 0:
            problems.append("per-tenant inflight limit must be finite and positive")
        return tuple(problems)


@dataclass(frozen=True)
class CapstoneDesign:
    owners: dict[ArchitectureConcern, ArchitectureComponent]
    capacity: CapacityEnvelope = CapacityEnvelope()
    tenant_scoped_run_keys: bool = True
    run_revision_cas: bool = True
    at_least_once_queue: bool = True
    lease_fencing: bool = True
    external_content_untrusted: bool = True
    exact_action_approval: bool = True
    sandbox_process_isolation: bool = True
    event_stream_rebuildable_from_run_truth: bool = True
    sensitive_telemetry_opt_in: bool = True
    admission_control: bool = True


@dataclass(frozen=True)
class DesignReview:
    violations: tuple[str, ...]

    @property
    def accepted(self) -> bool:
        return not self.violations


class FailureScenario(StrEnum):
    WORKER_CRASH = "worker_crash"
    DUPLICATE_DELIVERY = "duplicate_delivery"
    MALICIOUS_WEB_CONTENT = "malicious_web_content"
    MODEL_QUALITY_REGRESSION = "model_quality_regression"
    SSE_DISCONNECT = "sse_disconnect"
    RUN_STORE_UNAVAILABLE = "run_store_unavailable"
    AMBIGUOUS_SIDE_EFFECT = "ambiguous_side_effect"
    OVERLOAD = "overload"


@dataclass(frozen=True)
class FailureDrill:
    scenario: FailureScenario
    detect: tuple[str, ...]
    contain: tuple[str, ...]
    recover: tuple[str, ...]
    invariant: str


class CapstoneArchitectureReviewer:
    """Review the final Agent architecture by ownership and failure invariants.

    The goal is not to bless one vendor stack. It is to reject responsibility
    confusion: Queue delivery must not become Run truth, LangGraph checkpoints do
    not authorize users, the LLM cannot grant tool permissions, SSE is a client
    projection rather than the authoritative product database, and a subprocess
    is not automatically a hostile-code sandbox.
    """

    def review(self, design: CapstoneDesign) -> DesignReview:
        problems: list[str] = list(design.capacity.violations())

        for concern, expected_owner in REFERENCE_OWNERS.items():
            actual = design.owners.get(concern)
            if actual is None:
                problems.append(f"missing owner for {concern.value}")
            elif actual is not expected_owner:
                problems.append(
                    f"{concern.value} must be owned by {expected_owner.value}, not {actual.value}"
                )

        invariants = (
            (design.tenant_scoped_run_keys, "Run state must be tenant scoped"),
            (design.run_revision_cas, "Run mutations need optimistic revision/CAS or an equivalent concurrency guard"),
            (design.at_least_once_queue, "Queue consumers must tolerate duplicate delivery"),
            (design.lease_fencing, "multi-worker execution needs lease/fencing or an equivalent stale-owner guard"),
            (design.external_content_untrusted, "external Browser/RAG/file content must not be treated as trusted authority"),
            (design.exact_action_approval, "high-risk approval must bind to the exact proposed action"),
            (design.sandbox_process_isolation, "hostile generated code needs a real isolation boundary beyond helper path checks"),
            (design.event_stream_rebuildable_from_run_truth, "client event streams must be recoverable from authoritative Run state"),
            (design.sensitive_telemetry_opt_in, "raw prompts/tool payloads must not be default telemetry"),
            (design.admission_control, "the service needs finite admission/backpressure limits"),
        )
        problems.extend(message for enabled, message in invariants if not enabled)
        return DesignReview(violations=tuple(problems))


def reference_design() -> CapstoneDesign:
    return CapstoneDesign(owners=dict(REFERENCE_OWNERS))


def failure_drill(scenario: FailureScenario) -> FailureDrill:
    drills: dict[FailureScenario, FailureDrill] = {
        FailureScenario.WORKER_CRASH: FailureDrill(
            scenario=scenario,
            detect=("lease heartbeat expires", "runtime trace marks abandoned owner"),
            contain=("old lease stops authorizing mutations", "fencing rejects zombie writes"),
            recover=("watchdog requeues from latest checkpoint", "new Worker claims a higher fencing token"),
            invariant="at most one current Worker may mutate authoritative Run execution state",
        ),
        FailureScenario.DUPLICATE_DELIVERY: FailureDrill(
            scenario=scenario,
            detect=("same logical Run attempt is delivered again",),
            contain=("idempotent claim rejects active/stale duplicate",),
            recover=("existing owner continues; duplicate delivery is discarded/acked safely",),
            invariant="at-least-once delivery must not create a second Run owner",
        ),
        FailureScenario.MALICIOUS_WEB_CONTENT: FailureDrill(
            scenario=scenario,
            detect=("Browser/RAG/file provenance is external_untrusted", "security telemetry may flag injection signals"),
            contain=("RunAuthority cannot be expanded by prompt text", "secret/network/tool scopes stay host controlled"),
            recover=("request exact human approval for tainted high-risk actions", "execute generated code only inside the sandbox boundary"),
            invariant="untrusted content may influence reasoning but cannot grant capability",
        ),
        FailureScenario.MODEL_QUALITY_REGRESSION: FailureDrill(
            scenario=scenario,
            detect=("golden/online eval score drops", "compare traces, cost, latency and failure clusters against baseline"),
            contain=("stop rollout or route affected traffic to the known-good configuration",),
            recover=("identify model/retrieval/tool/runtime layer", "fix the regressed layer and rerun regression gates"),
            invariant="green HTTP/tool spans do not imply acceptable answer quality",
        ),
        FailureScenario.SSE_DISCONNECT: FailureDrill(
            scenario=scenario,
            detect=("client connection closes", "client retains Last-Event-ID"),
            contain=("do not cancel the authoritative Run merely because one projection disconnected",),
            recover=("replay retained events after Last-Event-ID", "if retention is gone, GET Run truth and establish a new stream baseline"),
            invariant="SSE is a projection of Run progress, not the source of Run truth",
        ),
        FailureScenario.RUN_STORE_UNAVAILABLE: FailureDrill(
            scenario=scenario,
            detect=("readiness dependency check fails", "RunStore error rate spikes"),
            contain=("readiness becomes unhealthy", "stop accepting state-changing commands that cannot be durably recorded"),
            recover=("restore shared RunStore", "reconcile Queue/lease/checkpoint work against authoritative Run records"),
            invariant="when Run truth is unavailable, the system must not invent state from Queue or checkpoints",
        ),
        FailureScenario.AMBIGUOUS_SIDE_EFFECT: FailureDrill(
            scenario=scenario,
            detect=("tool checkpoint is IN_FLIGHT when Worker/transport fails",),
            contain=("do not blindly replay a non-idempotent effect",),
            recover=("reuse committed result when known", "retry only replay-safe/idempotent effects", "otherwise reconcile external reality"),
            invariant="the system never claims universal exactly-once for external side effects",
        ),
        FailureScenario.OVERLOAD: FailureDrill(
            scenario=scenario,
            detect=("queue depth/tenant inflight/queue wait crosses admission thresholds",),
            contain=("reject or defer new work with explicit retry guidance", "protect downstream rate and connection budgets"),
            recover=("drain backlog", "scale the actual bottleneck after observability identifies it"),
            invariant="bounded overload is safer than accepting unbounded work",
        ),
    }
    return drills[scenario]
