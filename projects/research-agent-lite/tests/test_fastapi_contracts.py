from fastapi.testclient import TestClient

from app.fastapi_app import create_app
from app.langgraph_production import ProductionGraphBridge


def client_with_bridge() -> tuple[TestClient, ProductionGraphBridge]:
    bridge = ProductionGraphBridge()
    return TestClient(create_app(bridge=bridge)), bridge


def test_v51_post_runs_returns_201_and_only_enqueues_work() -> None:
    client, bridge = client_with_bridge()

    response = client.post(
        "/runs",
        headers={"X-Tenant-ID": "tenant-a"},
        json={"objective": "  compare   two papers  ", "approval_required": False},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["objective"] == "compare two papers"
    assert body["status"] == "queued"
    assert body["revision"] == 1
    assert len(bridge.control.queue) == 1


def test_v51_get_run_returns_200_then_missing_run_returns_404() -> None:
    client, _ = client_with_bridge()
    created = client.post(
        "/runs",
        headers={"X-Tenant-ID": "tenant-a"},
        json={"objective": "compare methods"},
    ).json()

    found = client.get(
        f"/runs/{created['id']}",
        headers={"X-Tenant-ID": "tenant-a"},
    )
    assert found.status_code == 200
    assert found.json()["id"] == created["id"]

    missing = client.get(
        "/runs/run-does-not-exist",
        headers={"X-Tenant-ID": "tenant-a"},
    )
    assert missing.status_code == 404


def test_v52_request_validation_rejects_blank_objective_and_unknown_fields() -> None:
    client, _ = client_with_bridge()

    blank = client.post(
        "/runs",
        headers={"X-Tenant-ID": "tenant-a"},
        json={"objective": "   "},
    )
    assert blank.status_code == 422

    extra = client.post(
        "/runs",
        headers={"X-Tenant-ID": "tenant-a"},
        json={"objective": "paper search", "admin": True},
    )
    assert extra.status_code == 422


def test_v52_tenant_dependency_is_required_and_other_tenant_cannot_enumerate_run() -> None:
    client, _ = client_with_bridge()

    no_tenant = client.post("/runs", json={"objective": "paper search"})
    assert no_tenant.status_code == 422

    created = client.post(
        "/runs",
        headers={"X-Tenant-ID": "tenant-a"},
        json={"objective": "private research"},
    ).json()

    other_tenant = client.get(
        f"/runs/{created['id']}",
        headers={"X-Tenant-ID": "tenant-b"},
    )
    assert other_tenant.status_code == 404


def test_v52_response_model_filters_internal_control_plane_fields() -> None:
    client, _ = client_with_bridge()
    body = client.post(
        "/runs",
        headers={"X-Tenant-ID": "tenant-a"},
        json={"objective": "paper search", "approval_required": True},
    ).json()

    assert set(body) == {
        "id",
        "objective",
        "status",
        "revision",
        "cancel_requested",
    }
    assert "tenant_id" not in body
    assert "current_checkpoint_id" not in body
    assert "approval_request_id" not in body
    assert "budget" not in body


def test_v52_openapi_documents_run_contract_and_required_tenant_header() -> None:
    client, _ = client_with_bridge()
    schema = client.get("/openapi.json").json()

    assert "/runs" in schema["paths"]
    assert "/runs/{run_id}" in schema["paths"]
    assert schema["paths"]["/runs"]["post"]["responses"]["201"]

    parameters = schema["paths"]["/runs"]["post"]["parameters"]
    tenant_header = next(item for item in parameters if item["name"] == "X-Tenant-ID")
    assert tenant_header["in"] == "header"
    assert tenant_header["required"] is True
