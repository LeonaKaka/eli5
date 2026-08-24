# Research Assistant v5.4

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

Python closed at **v1.0**, LLM Application Engineering at **v2.0**, RAG at **v3.0**, Agent Engineering at **v4.0**, LangChain / LangGraph at **v5.0**, and the FastAPI track now evolves the same system toward **v6.0**.

## FastAPI increments

- **v5.1** — first real `FastAPI()` application around the product Run model; `POST /runs` creates a queued Run and `GET /runs/{run_id}` reads it.
- **v5.2** — explicit Pydantic request/response contracts, `Annotated + Depends` tenant/runtime dependencies, anti-enumeration lookup and public response filtering.
- **v5.3** — explicit request/worker lifetime separation; `run_one_worker_tick()` pops durable jobs outside the HTTP request and can offload the current synchronous Graph adapter with `anyio.to_thread.run_sync()` inside the worker.
- **v5.4** — native FastAPI SSE via `EventSourceResponse` / `ServerSentEvent`, bounded client-safe Run event log, `Last-Event-ID` replay, retention-gap detection and tenant-scoped `/runs/{run_id}/stream`.

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
```

They currently require the teaching header `X-Tenant-ID`. It is deliberately **not** production authentication; lesson 06 replaces this trust model with authenticated identity + authorization.

## Current structure

```text
app/
├── fastapi_app.py               # v5.1-v5.4 HTTP contracts + SSE endpoint
├── fastapi_worker.py            # v5.3 separate async worker adapter
├── fastapi_streaming.py         # v5.4 client-safe Run event log/schema
├── langgraph_production.py      # v5.0 product control-plane ↔ LangGraph bridge
├── production.py                # tenant RunStore / Queue / optimistic revisions / cancel
└── ...

tests/
├── test_fastapi_contracts.py
├── test_fastapi_async_sse.py
└── ...
```

## Async / Worker boundary

`async def` is an execution/concurrency choice, not a background-job guarantee. `POST /runs` still performs only short boundary work: validate, create the product Run and enqueue a job. It does not await a long Agent execution.

FastAPI runs normal `def` path operations/dependencies in a threadpool, but a normal utility function called directly from inside `async def` is still called directly. Short blocking SDK calls can therefore be isolated explicitly with thread offload. Long, durable Agent work belongs behind Queue/Worker regardless of syntax.

FastAPI `BackgroundTasks` remains useful for small same-process post-response work, but it is not the durability mechanism for this Agent: deployment restarts, multi-worker ownership, checkpoints, approval pauses and retry semantics remain in the existing control plane and Graph runtime.

## SSE boundary

The v5.4 stream endpoint uses FastAPI's native SSE response primitives. Run events first pass through `RunStreamEvent`, which contains only client-safe fields (`run_id`, event type, status/phase/progress/message). Tenant ids, checkpoint ids, internal approval ids, budgets and raw Graph state are not part of the SSE schema.

The teaching `InMemoryRunEventStore` is bounded and process-local. `Last-Event-ID` replays retained events with a larger sequence id. If the requested cursor has fallen behind retention, the API returns a conflict instead of pretending replay is complete; the client must refetch the current Run state and establish a new baseline.

A production multi-worker deployment needs a durable event log/pubsub backend. SSE connection lifetime is not Run ownership: a client disconnect does not cancel the Run, and a Worker does not depend on one browser connection staying alive.

## Tests added for v5.3-v5.4

`test_fastapi_async_sse.py` locks:

- a submitted Run remains `queued` until a separate worker tick executes the queued job
- the worker can complete the Run outside the HTTP request lifecycle
- `Last-Event-ID` replays only later SSE events
- SSE never dumps internal control-plane/Graph fields
- cross-tenant stream access returns the same 404-style boundary as ordinary Run lookup
- malformed `Last-Event-ID` is rejected before streaming begins
- a retention gap produces an explicit conflict instead of fake complete replay
- OpenAPI documents the SSE route and optional `Last-Event-ID` header

## What FastAPI still does not replace

FastAPI owns HTTP parsing, routing, dependency wiring, SSE serialization and OpenAPI. It does not replace durable queueing, worker claims/revisions, LangGraph checkpoint/interrupt semantics, authentication/authorization, side-effect idempotency, cancellation policy or durable event infrastructure.

## Next step

FastAPI 05–06: approval/cancel/idempotent command endpoints, then authenticated identity, authorization, Security dependencies and CORS/trusted-proxy boundaries.
