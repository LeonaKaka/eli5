import asyncio

from fastapi.testclient import TestClient

from app.fastapi_app import create_app
from app.fastapi_streaming import InMemoryRunEventStore, RunEventType
from app.fastapi_worker import run_one_worker_tick
from app.langgraph_production import ProductionGraphBridge


def client_stack(*, max_events_per_run: int = 200):
    bridge = ProductionGraphBridge()
    events = InMemoryRunEventStore(max_events_per_run=max_events_per_run)
    client = TestClient(create_app(bridge=bridge, event_store=events))
    return client, bridge, events


def test_v53_http_submission_stays_queued_until_separate_worker_executes_job() -> None:
    client, bridge, events = client_stack()

    created = client.post(
        "/runs",
        headers={"X-Tenant-ID": "tenant-a"},
        json={"objective": "compare papers"},
    )
    assert created.status_code == 201
    run_id = created.json()["id"]
    assert created.json()["status"] == "queued"
    assert len(bridge.control.queue) == 1

    before = client.get(
        f"/runs/{run_id}",
        headers={"X-Tenant-ID": "tenant-a"},
    )
    assert before.json()["status"] == "queued"

    tick = asyncio.run(run_one_worker_tick(bridge, events=events))
    assert tick.had_job is True
    assert tick.outcome is not None
    assert tick.outcome.run.status.value == "completed"

    after = client.get(
        f"/runs/{run_id}",
        headers={"X-Tenant-ID": "tenant-a"},
    )
    assert after.json()["status"] == "completed"


def test_v54_sse_replays_only_events_after_last_event_id() -> None:
    client, _, events = client_stack()
    created = client.post(
        "/runs",
        headers={"X-Tenant-ID": "tenant-a"},
        json={"objective": "paper search"},
    ).json()
    run_id = created["id"]

    events.append(
        tenant_id="tenant-a",
        run_id=run_id,
        event=RunEventType.PROGRESS,
        phase="retrieve",
        progress=35,
        message="retrieving evidence",
    )

    response = client.get(
        f"/runs/{run_id}/stream?follow=false",
        headers={
            "X-Tenant-ID": "tenant-a",
            "Last-Event-ID": "1",
        },
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "id: 2" in response.text
    assert "event: progress" in response.text
    assert "id: 1" not in response.text
    assert "retrieve" in response.text
    assert "35" in response.text


def test_v54_sse_public_projection_does_not_dump_internal_run_or_graph_fields() -> None:
    client, bridge, events = client_stack()
    created = client.post(
        "/runs",
        headers={"X-Tenant-ID": "tenant-a"},
        json={"objective": "paper search", "approval_required": True},
    ).json()
    run_id = created["id"]

    tick = asyncio.run(run_one_worker_tick(bridge, events=events))
    assert tick.outcome is not None
    assert tick.outcome.interrupted is True

    response = client.get(
        f"/runs/{run_id}/stream?follow=false",
        headers={"X-Tenant-ID": "tenant-a"},
    )
    assert response.status_code == 200
    assert "event: run_created" in response.text
    assert "event: approval_required" in response.text
    assert "tenant_id" not in response.text
    assert "current_checkpoint_id" not in response.text
    assert "approval_request_id" not in response.text
    assert "budget" not in response.text
    assert "__interrupt__" not in response.text


def test_v54_cross_tenant_stream_lookup_is_not_enumerable() -> None:
    client, _, _ = client_stack()
    created = client.post(
        "/runs",
        headers={"X-Tenant-ID": "tenant-a"},
        json={"objective": "private research"},
    ).json()

    response = client.get(
        f"/runs/{created['id']}/stream?follow=false",
        headers={"X-Tenant-ID": "tenant-b"},
    )
    assert response.status_code == 404


def test_v54_invalid_last_event_id_returns_400_before_stream_starts() -> None:
    client, _, _ = client_stack()
    created = client.post(
        "/runs",
        headers={"X-Tenant-ID": "tenant-a"},
        json={"objective": "paper search"},
    ).json()

    response = client.get(
        f"/runs/{created['id']}/stream?follow=false",
        headers={"X-Tenant-ID": "tenant-a", "Last-Event-ID": "not-an-int"},
    )
    assert response.status_code == 400


def test_v54_retention_gap_returns_conflict_instead_of_fake_complete_replay() -> None:
    client, _, events = client_stack(max_events_per_run=2)
    created = client.post(
        "/runs",
        headers={"X-Tenant-ID": "tenant-a"},
        json={"objective": "paper search"},
    ).json()
    run_id = created["id"]

    events.append(
        tenant_id="tenant-a",
        run_id=run_id,
        event=RunEventType.PROGRESS,
        phase="retrieve",
        progress=25,
    )
    events.append(
        tenant_id="tenant-a",
        run_id=run_id,
        event=RunEventType.PROGRESS,
        phase="rerank",
        progress=60,
    )

    response = client.get(
        f"/runs/{run_id}/stream?follow=false",
        headers={"X-Tenant-ID": "tenant-a", "Last-Event-ID": "0"},
    )
    assert response.status_code == 409
    assert "no longer retained" in response.json()["detail"]


def test_v54_openapi_documents_sse_route_and_last_event_id_header() -> None:
    client, _, _ = client_stack()
    schema = client.get("/openapi.json").json()
    operation = schema["paths"]["/runs/{run_id}/stream"]["get"]

    parameters = operation["parameters"]
    last_event = next(item for item in parameters if item["name"] == "Last-Event-ID")
    assert last_event["in"] == "header"
    assert last_event["required"] is False
