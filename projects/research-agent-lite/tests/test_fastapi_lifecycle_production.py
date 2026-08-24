import asyncio

import pytest
from fastapi.testclient import TestClient

from app.fastapi_lifecycle import ManagedDependency, RuntimeResourceManager
from app.fastapi_service import (
    DeploymentProfile,
    audit_deployment,
    build_service,
    teaching_components,
)
from app.fastapi_worker import run_one_worker_tick


OWNER_A = {"Authorization": "Bearer demo-owner-a"}


def test_v59_lifespan_starts_resources_and_closes_them_after_client_context() -> None:
    manager = RuntimeResourceManager(
        [
            ManagedDependency("run_store"),
            ManagedDependency("job_queue"),
        ]
    )
    components = teaching_components()
    components.resources = manager
    app = build_service(components=components)

    assert manager.started is False
    with TestClient(app) as client:
        assert manager.started is True
        ready = client.get("/health/ready")
        assert ready.status_code == 200
        assert ready.json()["status"] == "ready"

    assert manager.started is False
    assert manager.closed is True
    assert all(dependency.closed for dependency in manager.dependencies)


def test_v59_required_dependency_failure_makes_ready_503_but_live_stays_200() -> None:
    manager = RuntimeResourceManager(
        [
            ManagedDependency("run_store"),
            ManagedDependency("job_queue"),
        ]
    )
    components = teaching_components()
    components.resources = manager
    app = build_service(components=components)

    with TestClient(app) as client:
        manager.set_ready("job_queue", False)

        live = client.get("/health/live")
        ready = client.get("/health/ready")

        assert live.status_code == 200
        assert live.json() == {"status": "live", "checks": []}
        assert ready.status_code == 503
        assert ready.json()["status"] == "not_ready"
        assert any(
            check["name"] == "job_queue" and check["ready"] is False
            for check in ready.json()["checks"]
        )

        manager.set_ready("job_queue", True)
        assert client.get("/health/ready").status_code == 200


def test_v59_optional_dependency_can_be_unready_without_removing_service_from_traffic() -> None:
    manager = RuntimeResourceManager(
        [
            ManagedDependency("run_store"),
            ManagedDependency("analytics_sink", required=False, ready_on_start=False),
        ]
    )
    components = teaching_components()
    components.resources = manager
    app = build_service(components=components)

    with TestClient(app) as client:
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"
        analytics = next(
            check for check in response.json()["checks"] if check["name"] == "analytics_sink"
        )
        assert analytics == {"name": "analytics_sink", "required": False, "ready": False}


def test_v59_startup_failure_cleans_up_resources_that_already_started() -> None:
    first = ManagedDependency("first")
    broken = ManagedDependency("broken", fail_on_start=True)
    manager = RuntimeResourceManager([first, broken])

    with pytest.raises(RuntimeError, match="failed to start dependency"):
        asyncio.run(manager.start())

    assert first.closed is True
    assert first.started is False
    assert manager.started is False


def test_v60_production_profile_rejects_process_local_teaching_adapters() -> None:
    components = teaching_components()
    audit = audit_deployment(components, profile=DeploymentProfile.PRODUCTION)

    assert audit.accepted is False
    joined = "\n".join(audit.violations)
    assert "RunStore is process-local" in joined
    assert "RunQueue is process-local" in joined
    assert "checkpointer is in-memory" in joined
    assert "event log is process-local" in joined
    assert "Idempotency registry is process-local" in joined
    assert "DemoTokenAuthenticator" in joined

    with pytest.raises(RuntimeError, match="production deployment audit failed"):
        build_service(profile=DeploymentProfile.PRODUCTION, components=components)


def test_v60_composition_root_keeps_http_worker_graph_boundaries_intact() -> None:
    components = teaching_components()
    app = build_service(components=components)

    with TestClient(app) as client:
        created = client.post(
            "/runs",
            headers=OWNER_A,
            json={"objective": "final v6 integration"},
        )
        assert created.status_code == 201
        run_id = created.json()["id"]
        assert created.json()["status"] == "queued"

        tick = asyncio.run(run_one_worker_tick(components.bridge, events=components.events))
        assert tick.had_job is True
        assert tick.outcome is not None
        assert tick.outcome.run.status.value == "completed"

        finished = client.get(f"/runs/{run_id}", headers=OWNER_A)
        assert finished.status_code == 200
        assert finished.json()["status"] == "completed"


def test_v60_openapi_exposes_health_contract_without_bearer_requirement() -> None:
    app = build_service()
    client = TestClient(app)
    schema = client.get("/openapi.json").json()

    assert schema["info"]["version"] == "6.0.0"
    live = schema["paths"]["/health/live"]["get"]
    ready = schema["paths"]["/health/ready"]["get"]
    assert "security" not in live
    assert "security" not in ready
    assert "503" in ready["responses"]
