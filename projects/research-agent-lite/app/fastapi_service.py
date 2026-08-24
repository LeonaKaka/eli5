from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from fastapi import FastAPI

from .fastapi_commands import InMemoryIdempotencyStore
from .fastapi_lifecycle import RuntimeResourceManager
from .fastapi_security import DemoTokenAuthenticator
from .fastapi_streaming import InMemoryRunEventStore
from .langgraph_production import ProductionGraphBridge
from .production import InMemoryRunQueue, InMemoryRunStore


class DeploymentProfile(StrEnum):
    TEACHING = "teaching"
    PRODUCTION = "production"


@dataclass
class ServiceComponents:
    bridge: ProductionGraphBridge
    events: InMemoryRunEventStore
    idempotency: InMemoryIdempotencyStore
    authenticator: DemoTokenAuthenticator
    resources: RuntimeResourceManager


@dataclass(frozen=True)
class DeploymentAudit:
    profile: DeploymentProfile
    violations: tuple[str, ...]

    @property
    def accepted(self) -> bool:
        return not self.violations


def teaching_components() -> ServiceComponents:
    return ServiceComponents(
        bridge=ProductionGraphBridge(),
        events=InMemoryRunEventStore(),
        idempotency=InMemoryIdempotencyStore(),
        authenticator=DemoTokenAuthenticator(),
        resources=RuntimeResourceManager(),
    )


def audit_deployment(
    components: ServiceComponents,
    *,
    profile: DeploymentProfile,
) -> DeploymentAudit:
    """Reject process-local durability when the caller claims production.

    This is deliberately strict: the v6.0 course closes the API architecture,
    not the infrastructure migration. Docker/deployment lessons will replace
    these teaching adapters with external durable services.
    """

    if profile is DeploymentProfile.TEACHING:
        return DeploymentAudit(profile=profile, violations=())

    violations: list[str] = []
    control = components.bridge.control
    if isinstance(control.store, InMemoryRunStore):
        violations.append("RunStore is process-local; production needs durable shared storage")
    if isinstance(control.queue, InMemoryRunQueue):
        violations.append("RunQueue is process-local; production needs an external durable queue")
    if components.bridge.checkpointer.__class__.__name__ == "InMemorySaver":
        violations.append("LangGraph checkpointer is in-memory; production needs durable checkpoints")
    if isinstance(components.events, InMemoryRunEventStore):
        violations.append("SSE event log is process-local; production needs shared retained event storage")
    if isinstance(components.idempotency, InMemoryIdempotencyStore):
        violations.append("Idempotency registry is process-local; production needs atomic shared storage")
    if isinstance(components.authenticator, DemoTokenAuthenticator):
        violations.append("DemoTokenAuthenticator is teaching-only; production needs real identity validation")
    if components.bridge.__class__ is ProductionGraphBridge:
        violations.append(
            "ProductionGraphBridge still keeps approval policy/resume metadata in process memory"
        )
    return DeploymentAudit(profile=profile, violations=tuple(violations))


def build_service(
    *,
    profile: DeploymentProfile = DeploymentProfile.TEACHING,
    components: ServiceComponents | None = None,
) -> FastAPI:
    """Final v6.0 composition root.

    Teaching mode is runnable without external infrastructure. Production mode
    refuses to start with known process-local safety/durability adapters.
    """

    selected = components or teaching_components()
    audit = audit_deployment(selected, profile=profile)
    if not audit.accepted:
        formatted = "\n - ".join(audit.violations)
        raise RuntimeError(f"production deployment audit failed:\n - {formatted}")

    # Import here to keep fastapi_app independent from this higher-level
    # composition root and avoid a circular import.
    from .fastapi_app import create_app

    app = create_app(
        bridge=selected.bridge,
        event_store=selected.events,
        idempotency_store=selected.idempotency,
        authenticator=selected.authenticator,
        resource_manager=selected.resources,
    )
    app.state.deployment_profile = profile.value
    app.state.deployment_audit = audit
    return app
