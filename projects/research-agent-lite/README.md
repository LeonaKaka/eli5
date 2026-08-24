# Research Assistant v5.6

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

Python closed at **v1.0**, LLM Application Engineering at **v2.0**, RAG at **v3.0**, Agent Engineering at **v4.0**, LangChain / LangGraph at **v5.0**, and the FastAPI track now evolves the same system toward **v6.0**.

## FastAPI increments

- **v5.1** — first real `FastAPI()` application around the product Run model; `POST /runs` creates a queued Run and `GET /runs/{run_id}` reads it.
- **v5.2** — explicit Pydantic request/response contracts, dependency boundaries, anti-enumeration lookup and public response filtering.
- **v5.3** — explicit request/worker lifetime separation; `run_one_worker_tick()` executes durable work outside the HTTP request.
- **v5.4** — native FastAPI SSE, bounded client-safe Run event log, `Last-Event-ID` replay and retention-gap detection.
- **v5.5** — approval/cancel command endpoints, public Run ETags, strong `If-Match` preconditions and an atomic teaching `Idempotency-Key` execute-once registry.
- **v5.6** — `HTTPBearer` authentication, `Principal(subject, tenant_id, permissions)`, route-level permission dependencies, tenant derivation from authenticated identity, explicit credentialed CORS and proxy-trust guidance.

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

The provider-free teaching authenticator accepts these demo bearer tokens:

```text
demo-owner-a   → tenant-a · read/create/approve/cancel
demo-viewer-a  → tenant-a · read only
demo-owner-b   → tenant-b · read/create/approve/cancel
```

Example:

```text
Authorization: Bearer demo-owner-a
```

These are not production credentials. They exist only to make authentication/authorization behavior deterministic without an external identity provider.

## Current structure

```text
app/
├── fastapi_app.py               # HTTP routes / SSE / command endpoints / CORS wiring
├── fastapi_worker.py            # separate async worker adapter
├── fastapi_streaming.py         # client-safe Run event log/schema
├── fastapi_commands.py          # ETag / If-Match / Idempotency-Key contracts
├── fastapi_security.py          # Bearer auth / Principal / permission dependencies
├── langgraph_production.py      # product control-plane ↔ LangGraph bridge
├── production.py                # tenant RunStore / Queue / optimistic revisions / cancel
└── ...

tests/
├── test_fastapi_contracts.py
├── test_fastapi_async_sse.py
├── test_fastapi_commands_security.py
└── ...
```

## Command boundary

All public Run JSON responses expose a strong ETag derived from the Run revision, e.g. `ETag: "7"`. Approval and cancellation commands require `If-Match` plus `Idempotency-Key`.

The two mechanisms solve different problems:

- `If-Match` rejects a command based on stale Run state (`412 Precondition Failed`).
- `Idempotency-Key` binds one logical command to one fingerprint/result so network retries replay the original response instead of re-executing it.

Missing preconditions return 428. Reusing one idempotency key for a different command returns 409. The teaching in-memory registry keeps lookup → execute → remember inside one lock so same-process concurrent retries cannot both execute. Production needs a durable shared equivalent with atomic reservation/create-if-absent behavior across API replicas.

Cancellation preserves the earlier control-plane semantics: queued/waiting runs may cancel immediately, while actively running work enters `CANCELLING` until a Worker confirms a safe boundary. HTTP cancellation still cannot roll back an already-executed external side effect.

## Authentication / authorization boundary

Tenant scope no longer comes from `X-Tenant-ID`. `HTTPBearer` extracts credentials, `DemoTokenAuthenticator` produces a Principal, and route dependencies require specific permissions:

```text
runs:read
runs:create
runs:approve
runs:cancel
```

Resource lookup always uses `principal.tenant_id`. A client can send a fake `X-Tenant-ID`, but it has no effect on authorization. Cross-tenant lookup continues to return 404 to avoid resource enumeration after authentication/permission checks.

The demo authenticator is not token validation guidance. A production adapter must validate the real identity mechanism's signatures/issuer/audience/expiry/revocation or equivalent session/API-key contract.

## CORS / proxy boundary

The application uses explicit origins, methods and request headers with `allow_credentials=True`; it does not combine credentialed requests with wildcard origins. CORS only controls browser cross-origin access and does not replace authentication or authorization.

Forwarded headers are a server/proxy trust concern. Only headers from configured trusted proxies should influence client IP/scheme/host interpretation; arbitrary client `X-Forwarded-*` headers are not identity.

## Existing boundaries still apply

FastAPI does not replace durable queueing, worker claims/revisions, LangGraph checkpoint/interrupt semantics, side-effect idempotency, cancellation policy or durable event infrastructure. SSE connection lifetime is still not Run ownership.

## Next step

FastAPI 07–08: replace scattered `HTTPException` shapes with a stable public error contract/exception handlers, then use dependency overrides and contract-focused tests to separate endpoint-unit tests from integration tests.
