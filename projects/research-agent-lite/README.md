# Research Assistant v5.8

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

Python closed at **v1.0**, LLM Application Engineering at **v2.0**, RAG at **v3.0**, Agent Engineering at **v4.0**, LangChain / LangGraph at **v5.0**, and the FastAPI track now evolves the same system toward **v6.0**.

## FastAPI increments

- **v5.1** — first real `FastAPI()` Run resource API
- **v5.2** — explicit request/response contracts and dependency boundaries
- **v5.3** — HTTP request lifetime separated from durable Worker lifetime
- **v5.4** — native SSE, client-safe event projection, `Last-Event-ID` replay and retention gaps
- **v5.5** — approval/cancel commands, ETag/`If-Match`, atomic teaching `Idempotency-Key` execution
- **v5.6** — `HTTPBearer`, Principal permissions, tenant derivation, CORS and proxy-trust boundaries
- **v5.7** — stable `ProblemDetails`, request correlation, validation/HTTP/500 exception handlers and documented error responses
- **v5.8** — dependency overrides, endpoint-unit vs integration boundaries and selective OpenAPI contract tests

Current FastAPI reference line used by the course: `fastapi>=0.141,<1` with Pydantic v2.

## Run

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
uvicorn app.fastapi_app:app --reload
```

Current public routes:

```text
POST /runs
GET  /runs/{run_id}
GET  /runs/{run_id}/stream
POST /runs/{run_id}/approvals/{approval_request_id}
POST /runs/{run_id}/cancel
```

Provider-free demo bearer tokens remain deterministic teaching credentials:

```text
demo-owner-a   → tenant-a · read/create/approve/cancel
demo-viewer-a  → tenant-a · read only
demo-owner-b   → tenant-b · read/create/approve/cancel
```

## Current structure

```text
app/
├── fastapi_app.py               # routes / SSE / commands / CORS / error wiring
├── fastapi_worker.py            # separate Worker adapter
├── fastapi_streaming.py         # client-safe event log/schema
├── fastapi_commands.py          # ETag / If-Match / Idempotency-Key
├── fastapi_security.py          # Bearer / Principal / permission dependencies
├── fastapi_errors.py            # ProblemDetails / request id / exception handlers
├── langgraph_production.py      # product control-plane ↔ LangGraph bridge
└── production.py                # tenant RunStore / Queue / optimistic revisions

tests/
├── test_fastapi_contracts.py
├── test_fastapi_async_sse.py
├── test_fastapi_commands_security.py
├── test_fastapi_errors_testing.py
└── ...
```

## v5.7 public error boundary

All client-facing errors now use a stable Problem Details-style schema:

```json
{
  "type": "urn:research-assistant:problem:precondition_failed",
  "title": "Precondition failed",
  "status": 412,
  "detail": "Run revision changed: ...",
  "instance": "/runs/run-42/cancel",
  "code": "precondition_failed",
  "request_id": "req-..."
}
```

`RequestValidationError` is projected to sanitized location/message/type issues instead of echoing the raw request body. FastAPI/Starlette HTTP exceptions keep their meaningful status codes and protocol headers such as `WWW-Authenticate`. Unexpected 500s return a generic public detail; real exception text and traces belong in private telemetry correlated by `request_id`.

Runtime exception handlers and OpenAPI documentation are separate responsibilities. The app therefore installs handlers **and** declares `ProblemDetails` through path-operation `responses=`.

## v5.8 testing boundary

FastAPI dependency injection is also the test seam. Endpoint-unit tests can override `get_current_principal` and `get_bridge` with deterministic fakes when the test only cares about routing, authorization wiring, response projection or ETag behavior.

That does **not** replace integration tests. Queue delivery, optimistic revision, idempotency, LangGraph interrupt/resume and tenant isolation stay real in tests when those mechanisms are the thing being verified. Over-mocking them would produce fast tests that prove only the fake behavior.

OpenAPI contract tests selectively lock externally important structure: Bearer security, command headers, `ProblemDetails`, important response codes and route existence. They intentionally avoid snapshotting every generated OpenAPI detail.

## Existing safety boundaries still apply

- tenant comes from authenticated Principal, not a client-supplied tenant header
- CORS is not authorization
- ETag preconditions and idempotency keys solve different retry/concurrency problems
- SSE connection lifetime is not Run ownership
- FastAPI does not replace durable Queue/Worker claims, LangGraph checkpoints, replay safety or side-effect idempotency
- a request id is correlation metadata, not identity or authorization

## Next step

FastAPI 09–10: lifespan/resource ownership + liveness/readiness, then close the backend at Research Assistant **v6.0** with the final production Agent API architecture.