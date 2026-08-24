# Research Assistant v6.0

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

Python closed at **v1.0**, LLM Application Engineering at **v2.0**, RAG at **v3.0**, Agent Engineering at **v4.0**, LangChain / LangGraph at **v5.0**, and FastAPI now closes the backend architecture at **v6.0**.

## FastAPI increments

- **v5.1** — first real `FastAPI()` Run resource API
- **v5.2** — explicit request/response contracts and dependency boundaries
- **v5.3** — HTTP request lifetime separated from durable Worker lifetime
- **v5.4** — native SSE, client-safe event projection, `Last-Event-ID` replay and retention gaps
- **v5.5** — approval/cancel commands, ETag/`If-Match`, atomic teaching `Idempotency-Key` execution
- **v5.6** — `HTTPBearer`, Principal permissions, tenant derivation, CORS and proxy-trust boundaries
- **v5.7** — stable `ProblemDetails`, request correlation, validation/HTTP/500 exception handlers and documented error responses
- **v5.8** — dependency overrides, endpoint-unit vs integration boundaries and selective OpenAPI contract tests
- **v5.9** — FastAPI lifespan resource ownership plus separate liveness/readiness probes and partial-start cleanup
- **v6.0** — final service composition root and deployment-profile audit that refuses process-local teaching adapters when the caller claims production

Current FastAPI reference line used by the course: `fastapi>=0.141,<1` with Pydantic v2.

## Run teaching profile

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
uvicorn app.fastapi_app:app --reload
```

The default `app.fastapi_app:app` remains the provider-free teaching service. The explicit v6 composition root is:

```python
from app.fastapi_service import build_service, DeploymentProfile

app = build_service(profile=DeploymentProfile.TEACHING)
```

Current public routes:

```text
GET  /health/live
GET  /health/ready
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
├── fastapi_app.py               # routes / SSE / commands / health / CORS / error wiring
├── fastapi_worker.py            # separate Worker adapter
├── fastapi_streaming.py         # client-safe event log/schema
├── fastapi_commands.py          # ETag / If-Match / Idempotency-Key
├── fastapi_security.py          # Bearer / Principal / permission dependencies
├── fastapi_errors.py            # ProblemDetails / request id / exception handlers
├── fastapi_lifecycle.py         # lifespan / resource ownership / live + ready
├── fastapi_service.py           # v6 composition root / deployment profile audit
├── langgraph_production.py      # product control-plane ↔ LangGraph bridge
└── production.py                # tenant RunStore / Queue / optimistic revisions

tests/
├── test_fastapi_contracts.py
├── test_fastapi_async_sse.py
├── test_fastapi_commands_security.py
├── test_fastapi_errors_testing.py
├── test_fastapi_lifecycle_production.py
└── ...
```

## Public error and HTTP control boundary

All client-facing errors use the stable Problem Details-style schema introduced in v5.7. Mutating commands keep their distinct safety mechanisms:

- Bearer Principal → identity / tenant / action permission
- `If-Match` → stale-client protection against Run revision
- `Idempotency-Key` → network retry replay without second side effect
- approval request id → bind a human decision to one exact paused action
- `request_id` → private telemetry correlation only; never identity or authorization

## Lifespan / health boundary

`RuntimeResourceManager` owns process-scoped resources. Startup opens them once; shutdown closes them once. If startup fails partway through, resources that already started are closed before the exception escapes.

Operational probes are intentionally different:

```text
/health/live  → is this process/event loop alive enough to answer?
/health/ready → should the load balancer send new production traffic here?
```

A required queue/storage/checkpoint dependency can make readiness return 503 while liveness remains 200. Optional dependencies may be degraded without removing the whole API from traffic when product policy allows it.

## v6.0 deployment profile gate

The course intentionally keeps deterministic in-memory adapters so the whole system can run without external infrastructure. `DeploymentProfile.PRODUCTION` therefore audits the composition before app creation.

The default teaching stack is rejected as production because it still contains process-local state such as:

```text
InMemoryRunStore
InMemoryRunQueue
LangGraph InMemorySaver
InMemoryRunEventStore
InMemoryIdempotencyStore
DemoTokenAuthenticator
process-local approval/resume metadata in ProductionGraphBridge
```

This is deliberate. A Docker image that contains only these adapters can start, but it is not horizontally scalable or restart-safe. The next Docker/deployment track replaces these with durable/shared implementations rather than relabeling them production.

## Final ownership model

```text
FastAPI / application
  HTTP contracts · auth · tenant · Run resource · command policy

RunStore / Queue / Worker control plane
  product status · revision · cancellation · delivery · worker claim

LangGraph
  graph state · checkpoint · interrupt · resume semantics

External tool / infrastructure
  durable DB/queue/checkpointer/event log · downstream idempotency · identity provider
```

SSE is a client-safe projection, not authoritative Run state. LangGraph checkpoints are execution state, not tenant authorization. Queue delivery is not the Run database. Those boundaries remain explicit at v6.0.

## Next step

The backend learning line is closed at v6.0. The next core job-skill track is **Docker / containerization and multi-service deployment**: externalize the process-local adapters, containerize API/worker separately, add networking/config/secrets/volumes, then validate restart and multi-replica behavior.
