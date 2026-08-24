import asyncio

from fastapi.testclient import TestClient

from app.fastapi_app import create_app
from app.fastapi_streaming import InMemoryRunEventStore
from app.fastapi_worker import run_one_worker_tick
from app.langgraph_production import ProductionGraphBridge


OWNER_A = {"Authorization": "Bearer demo-owner-a"}
VIEWER_A = {"Authorization": "Bearer demo-viewer-a"}
OWNER_B = {"Authorization": "Bearer demo-owner-b"}


def client_stack():
    bridge = ProductionGraphBridge()
    events = InMemoryRunEventStore()
    client = TestClient(create_app(bridge=bridge, event_store=events))
    return client, bridge, events


def create_waiting_approval(client, bridge, events):
    created = client.post(
        "/runs",
        headers=OWNER_A,
        json={"objective": "send report", "approval_required": True},
    )
    run_id = created.json()["id"]
    tick = asyncio.run(run_one_worker_tick(bridge, events=events))
    assert tick.outcome is not None
    assert tick.outcome.interrupted is True
    record = bridge.control.store.get(run_id, tenant_id="tenant-a")
    assert record.approval_request_id is not None
    return run_id, record


def command_headers(*, etag: str, key: str, auth: dict[str, str] = OWNER_A):
    return {
        **auth,
        "If-Match": etag,
        "Idempotency-Key": key,
    }


def test_v55_approval_retry_replays_response_without_second_resume_job() -> None:
    client, bridge, events = client_stack()
    run_id, paused = create_waiting_approval(client, bridge, events)
    approval_id = paused.approval_request_id
    assert approval_id is not None

    first = client.post(
        f"/runs/{run_id}/approvals/{approval_id}",
        headers=command_headers(etag=f'"{paused.revision}"', key="approve-001"),
        json={"decision": "approve"},
    )
    assert first.status_code == 200
    assert first.json()["status"] == "queued"
    assert first.headers["idempotency-replayed"] == "false"
    assert len(bridge.control.queue) == 1

    retry = client.post(
        f"/runs/{run_id}/approvals/{approval_id}",
        headers=command_headers(etag=f'"{paused.revision}"', key="approve-001"),
        json={"decision": "approve"},
    )
    assert retry.status_code == 200
    assert retry.json() == first.json()
    assert retry.headers["etag"] == first.headers["etag"]
    assert retry.headers["idempotency-replayed"] == "true"
    assert len(bridge.control.queue) == 1


def test_v55_same_idempotency_key_cannot_change_approval_decision() -> None:
    client, bridge, events = client_stack()
    run_id, paused = create_waiting_approval(client, bridge, events)
    approval_id = paused.approval_request_id
    assert approval_id is not None
    headers = command_headers(etag=f'"{paused.revision}"', key="approval-key")

    approved = client.post(
        f"/runs/{run_id}/approvals/{approval_id}",
        headers=headers,
        json={"decision": "approve"},
    )
    assert approved.status_code == 200

    changed = client.post(
        f"/runs/{run_id}/approvals/{approval_id}",
        headers=headers,
        json={"decision": "reject"},
    )
    assert changed.status_code == 409
    assert "different command" in changed.json()["detail"]


def test_v55_new_command_with_stale_revision_gets_412_and_missing_precondition_gets_428() -> None:
    client, bridge, events = client_stack()
    run_id, paused = create_waiting_approval(client, bridge, events)
    approval_id = paused.approval_request_id
    assert approval_id is not None

    missing = client.post(
        f"/runs/{run_id}/approvals/{approval_id}",
        headers={**OWNER_A, "Idempotency-Key": "missing-if-match"},
        json={"decision": "approve"},
    )
    assert missing.status_code == 428

    stale = client.post(
        f"/runs/{run_id}/approvals/{approval_id}",
        headers=command_headers(etag='"1"', key="stale-command"),
        json={"decision": "approve"},
    )
    assert stale.status_code == 412


def test_v55_cancel_is_idempotent_and_exposes_new_etag() -> None:
    client, bridge, _ = client_stack()
    created = client.post(
        "/runs",
        headers=OWNER_A,
        json={"objective": "queued research"},
    )
    run_id = created.json()["id"]
    original_etag = created.headers["etag"]

    first = client.post(
        f"/runs/{run_id}/cancel",
        headers=command_headers(etag=original_etag, key="cancel-001"),
    )
    assert first.status_code == 200
    assert first.json()["status"] == "cancelled"
    assert first.headers["etag"] != original_etag
    assert first.headers["idempotency-replayed"] == "false"
    assert len(bridge.control.queue) == 1  # stale START delivery remains but cannot claim the cancelled revision

    retry = client.post(
        f"/runs/{run_id}/cancel",
        headers=command_headers(etag=original_etag, key="cancel-001"),
    )
    assert retry.status_code == 200
    assert retry.json() == first.json()
    assert retry.headers["idempotency-replayed"] == "true"


def test_v56_authentication_and_permission_boundaries_are_separate() -> None:
    client, _, _ = client_stack()

    missing = client.get("/runs/anything")
    assert missing.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"

    invalid = client.get(
        "/runs/anything",
        headers={"Authorization": "Bearer not-valid"},
    )
    assert invalid.status_code == 401

    viewer_create = client.post(
        "/runs",
        headers=VIEWER_A,
        json={"objective": "not allowed"},
    )
    assert viewer_create.status_code == 403

    owner_created = client.post(
        "/runs",
        headers=OWNER_A,
        json={"objective": "viewer may read this"},
    ).json()
    viewer_read = client.get(
        f"/runs/{owner_created['id']}",
        headers=VIEWER_A,
    )
    assert viewer_read.status_code == 200

    viewer_cancel = client.post(
        f"/runs/{owner_created['id']}/cancel",
        headers=command_headers(etag='"1"', key="viewer-cancel", auth=VIEWER_A),
    )
    assert viewer_cancel.status_code == 403


def test_v56_tenant_is_derived_from_token_not_spoofed_header() -> None:
    client, bridge, _ = client_stack()

    created = client.post(
        "/runs",
        headers={**OWNER_A, "X-Tenant-ID": "tenant-b"},
        json={"objective": "tenant comes from authenticated principal"},
    )
    assert created.status_code == 201
    run_id = created.json()["id"]

    record = bridge.control.store.get(run_id, tenant_id="tenant-a")
    assert record.tenant_id == "tenant-a"

    other_tenant = client.get(f"/runs/{run_id}", headers=OWNER_B)
    assert other_tenant.status_code == 404


def test_v56_cors_allows_explicit_frontend_origin_with_credentials_not_wildcard() -> None:
    client, _, _ = client_stack()

    allowed = client.options(
        "/runs",
        headers={
            "Origin": "https://app.example.test",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "https://app.example.test"
    assert allowed.headers["access-control-allow-credentials"] == "true"

    blocked = client.options(
        "/runs",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )
    assert "access-control-allow-origin" not in blocked.headers


def test_v56_openapi_declares_bearer_security_and_command_headers() -> None:
    client, _, _ = client_stack()
    schema = client.get("/openapi.json").json()
    assert schema["components"]["securitySchemes"]["BearerAuth"]["type"] == "http"
    assert schema["components"]["securitySchemes"]["BearerAuth"]["scheme"] == "bearer"

    operation = schema["paths"]["/runs/{run_id}/cancel"]["post"]
    names = {item["name"] for item in operation["parameters"]}
    assert "If-Match" in names
    assert "Idempotency-Key" in names
    assert operation["security"] == [{"BearerAuth": []}]
