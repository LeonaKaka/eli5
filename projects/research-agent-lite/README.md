# Research Assistant v5.2

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

Python closed at **v1.0**, LLM Application Engineering at **v2.0**, RAG at **v3.0**, Agent Engineering at **v4.0**, LangChain / LangGraph at **v5.0**, and the FastAPI track now evolves the same system toward **v6.0**.

## FastAPI increments

- **v5.1** — first real `FastAPI()` application around the existing product Run model; `POST /runs` creates a queued Run and `GET /runs/{run_id}` reads it. Long Agent work remains behind the Queue/Worker boundary instead of executing inline in the request.
- **v5.2** — explicit Pydantic `CreateRunRequest` / `RunResponse`, `Annotated + Depends` tenant/runtime dependencies, tenant-scoped lookup, response filtering and OpenAPI-visible header requirements.

Current FastAPI reference line used by the course: `fastapi>=0.141,<1` with Pydantic v2. The project keeps `fastapi[standard]` so the local developer install also includes the standard server/test tooling.

## Run

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q

# Development HTTP server
uvicorn app.fastapi_app:app --reload
```

Then inspect `/docs` or `/openapi.json` and call:

```text
POST /runs
GET  /runs/{run_id}
```

Both currently require the teaching header `X-Tenant-ID`. It is deliberately **not** presented as production authentication; lesson 06 replaces that trust model with authenticated identity + authorization.

## Current structure

```text
app/
├── fastapi_app.py               # v5.1-v5.2 HTTP boundary / contracts / dependencies
├── langgraph_production.py      # v5.0 Product control-plane ↔ LangGraph bridge
├── production.py                # tenant RunStore / Queue / optimistic revisions / cancel
├── langgraph_observability.py   # middleware + stream concepts
├── langgraph_store.py           # Store / memory boundary
├── langgraph_interrupts.py      # durable pause/resume
└── ...

tests/
├── test_fastapi_contracts.py
├── test_langgraph_observability_production.py
└── ...
```

## HTTP boundary

`POST /runs` does **not** call `graph.invoke()` for a long-lived Agent run. It creates a product Run through `ProductionGraphBridge.submit()`, which records the Run and enqueues work. This keeps HTTP request lifetime separate from durable job lifetime.

The public `RunResponse` is intentionally smaller than internal `RunRecord`. Internal `tenant_id`, checkpoint ids, approval request ids and budgets are not returned merely because they exist in memory. The response model is an API projection, not a dump of the control-plane object.

## Tenant dependency boundary

`TenantContext` is injected through `Annotated[..., Depends(...)]`. The current header-derived tenant exists only so lessons 01–02 can demonstrate dependency wiring, tenant isolation and OpenAPI integration. A real client must not be able to self-assert any tenant simply by choosing a header value; later security lessons derive tenant/workspace scope from authenticated identity and explicit authorization.

Cross-tenant lookup currently returns the same 404 as a missing Run to avoid confirming another tenant's resource existence. This is a deliberate anti-enumeration choice, not a universal rule for every API.

## Tests added for v5.1-v5.2

`test_fastapi_contracts.py` locks:

- `POST /runs` → `201 Created`, normalized objective, `QUEUED` state and exactly one queued job
- `GET /runs/{id}` → 200; missing Run → 404
- blank body / unknown fields / missing required tenant header → 422
- another tenant cannot enumerate a Run
- public response does not leak internal control-plane fields
- generated OpenAPI includes the Run routes, 201 response and required `X-Tenant-ID` header

## What FastAPI does not replace

FastAPI owns HTTP parsing, routing, dependency wiring, response serialization and OpenAPI. It does not replace durable queueing, worker claims/revisions, LangGraph checkpoint/interrupt semantics, tenant authorization, side-effect idempotency or cancellation policy.

## Next step

FastAPI 03–04: async request boundaries / blocking work / Queue+Worker separation, then Server-Sent Events that project safe Run/Graph progress to clients without exposing internal debug state.
