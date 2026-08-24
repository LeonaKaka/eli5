from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.agent_control import RunStatus
from app.fastapi_app import create_app, get_bridge
from app.fastapi_security import Principal, RUN_READ, get_current_principal
from app.production import RunRecord


OWNER_A = {"Authorization": "Bearer demo-owner-a"}


class FakeRunStore:
    def __init__(self, record: RunRecord) -> None:
        self.record = record
        self.calls: list[tuple[str, str]] = []

    def get(self, run_id: str, *, tenant_id: str) -> RunRecord:
        self.calls.append((run_id, tenant_id))
        if run_id != self.record.id:
            raise KeyError(run_id)
        if tenant_id != self.record.tenant_id:
            raise PermissionError(tenant_id)
        return self.record.model_copy(deep=True)


class FakeBridge:
    def __init__(self, record: RunRecord) -> None:
        self.store = FakeRunStore(record)
        self.control = SimpleNamespace(store=self.store)


def test_v57_validation_error_uses_stable_problem_details_without_echoing_body() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/runs",
        headers=OWNER_A,
        json={"objective": "   ", "unexpected": "secret-input"},
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["status"] == 422
    assert body["instance"] == "/runs"
    assert body["request_id"] == response.headers["x-request-id"]
    assert body["errors"]
    assert "secret-input" not in response.text
    assert "traceback" not in response.text.lower()


def test_v57_http_errors_keep_semantics_and_correlation_headers() -> None:
    app = create_app()
    client = TestClient(app)

    unauthenticated = client.get("/runs/run-missing")
    assert unauthenticated.status_code == 401
    assert unauthenticated.headers["www-authenticate"] == "Bearer"
    assert unauthenticated.json()["code"] == "authentication_required"
    assert unauthenticated.json()["request_id"] == unauthenticated.headers["x-request-id"]

    missing = client.get("/runs/run-missing", headers=OWNER_A)
    assert missing.status_code == 404
    assert missing.json()["code"] == "not_found"
    assert missing.json()["detail"] == "run not found"


def test_v57_unhandled_exception_returns_generic_500_without_exception_text() -> None:
    app = create_app()

    @app.get("/_test/boom", include_in_schema=False)
    async def boom():
        raise RuntimeError("private-checkpoint-secret")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/_test/boom")

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "internal_error"
    assert response.json()["detail"] == "An unexpected server error occurred."
    assert "private-checkpoint-secret" not in response.text


def test_v58_dependency_overrides_isolate_endpoint_contract_from_auth_and_real_control_plane() -> None:
    record = RunRecord(
        id="run-unit",
        tenant_id="tenant-test",
        objective="fake dependency contract",
        status=RunStatus.QUEUED,
        revision=7,
    )
    fake_bridge = FakeBridge(record)
    app = create_app(bridge=fake_bridge)

    async def override_principal() -> Principal:
        return Principal(
            subject="test-user",
            tenant_id="tenant-test",
            permissions=frozenset({RUN_READ}),
        )

    def override_bridge() -> FakeBridge:
        return fake_bridge

    app.dependency_overrides[get_current_principal] = override_principal
    app.dependency_overrides[get_bridge] = override_bridge
    try:
        client = TestClient(app)
        response = client.get("/runs/run-unit")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "id": "run-unit",
        "objective": "fake dependency contract",
        "status": "queued",
        "revision": 7,
        "cancel_requested": False,
    }
    assert response.headers["etag"] == '"7"'
    assert fake_bridge.store.calls == [("run-unit", "tenant-test")]


def test_v58_openapi_locks_success_security_command_headers_and_problem_schema() -> None:
    app = create_app()
    client = TestClient(app)
    schema = client.get("/openapi.json").json()

    assert schema["info"]["version"] == "5.8.0"
    assert "BearerAuth" in schema["components"]["securitySchemes"]
    assert "ProblemDetails" in schema["components"]["schemas"]

    get_run = schema["paths"]["/runs/{run_id}"]["get"]
    assert get_run["security"] == [{"BearerAuth": []}]
    assert "404" in get_run["responses"]

    cancel = schema["paths"]["/runs/{run_id}/cancel"]["post"]
    header_names = {item["name"] for item in cancel["parameters"]}
    assert {"If-Match", "Idempotency-Key"}.issubset(header_names)
    assert {"409", "412", "428"}.issubset(cancel["responses"])


def test_v58_integration_boundary_is_not_replaced_by_dependency_override_tests() -> None:
    """A tiny integration smoke test still uses the real in-memory control plane."""

    app = create_app()
    client = TestClient(app)
    created = client.post(
        "/runs",
        headers=OWNER_A,
        json={"objective": "integration boundary"},
    )

    assert created.status_code == 201
    run_id = created.json()["id"]
    fetched = client.get(f"/runs/{run_id}", headers=OWNER_A)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == run_id
    assert fetched.json()["status"] == "queued"
