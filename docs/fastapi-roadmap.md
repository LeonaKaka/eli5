# FastAPI Roadmap

Scope: expose Research Assistant v5.0 as a real HTTP service without collapsing the durable Agent control-plane boundaries already learned. FastAPI owns HTTP contracts and dependency wiring; it does not replace the RunStore, Queue, Worker, LangGraph runtime, tenant policy or side-effect safety.

Current reference line: FastAPI 0.141.x, Pydantic v2.

Current progress: **06 / 10 live**, Research Assistant **v5.6**.

## 01 — API Boundary / ASGI / First Run API ✅
Build the first real service around the existing product run lifecycle. Understand ASGI request/response boundaries, `FastAPI()`, path operations, `POST /runs`, `GET /runs/{run_id}`, 201/200/404 semantics and automatic OpenAPI. The HTTP request only submits work; it does not execute a long Agent run inline.

## 02 — Pydantic Contracts / Depends / Tenant Context ✅
Use explicit request/response models, `Annotated + Depends`, dependency-derived request context and response filtering. Keep internal fields such as tenant identifiers, checkpoint ids and budgets out of the public response model. The temporary client-supplied tenant header from this lesson is explicitly replaced by authenticated identity in lesson 06.

## 03 — Async Boundary / Worker Separation ✅
Understand `async def`, blocking I/O, FastAPI threadpool behavior and why async syntax is not a background-job system. Keep long Agent execution behind Queue/Worker. Short blocking adapters may use explicit thread offload; `BackgroundTasks` is not presented as durable multi-worker execution.

## 04 — SSE Streaming ✅
Expose `/runs/{run_id}/stream` with native `EventSourceResponse` / `ServerSentEvent`. Use stable client-safe event types, sequence ids, `Last-Event-ID` replay, disconnect awareness and bounded retention. A retention gap is explicit rather than silently dropping history; raw Graph/debug/control-plane state is never the public stream schema.

## 05 — Approval / Cancel / Idempotent Commands ✅
Add exact approval and cancellation command endpoints. Public Run responses expose a revision ETag; mutating commands require strong `If-Match` preconditions plus `Idempotency-Key`. Same-key/same-command retries replay the original response without a second RESUME; key reuse with a different command is 409; stale revisions are 412 and missing preconditions are 428. The teaching idempotency adapter uses atomic single-process execute-once semantics and documents the need for durable cross-replica storage in production.

## 06 — Auth / Security / CORS / Trusted Boundaries ✅
Replace trusted `X-Tenant-ID` with Bearer authentication. A token becomes a `Principal(subject, tenant_id, permissions)`; route dependencies enforce `runs:read/create/approve/cancel`, and resource scope uses the tenant derived from authenticated identity. Add explicit credentialed CORS policy and distinguish browser origin policy from backend authorization. Document forwarded-header trust as a reverse-proxy/server boundary rather than trusting arbitrary client `X-Forwarded-*` input.

## 07 — Errors / Exception Handlers / Problem Details
Map domain failures to stable HTTP status/error schemas: validation, not found, forbidden, conflict, unavailable and internal errors. Use exception handlers without leaking stack traces or internal state.

## 08 — Testing / Dependency Overrides / OpenAPI Contract
Use `TestClient`/httpx, dependency overrides, fake control-plane adapters, tenant regressions, idempotency tests and OpenAPI/schema checks. Distinguish endpoint-unit tests from integration tests.

## 09 — Lifespan / Health / Readiness / Resource Management
Manage long-lived DB/HTTP/queue clients with lifespan. Separate liveness/readiness, connection-pool ownership, shutdown and startup failure behavior.

## 10 — Production Agent API Architecture
Close Research Assistant at v6.0: API → auth/dependencies → RunStore → Queue/Workers → LangGraph → Stream/HITL. Define deployment and observability boundaries while leaving container/orchestrator concerns for the Docker track.

## Project evolution
Continue `projects/research-agent-lite/` from Research Assistant v5.0:
- v5.1 first FastAPI application + POST/GET Run endpoints ✅
- v5.2 Pydantic public contracts + dependency boundary ✅
- v5.3 async request / worker lifetime separation ✅
- v5.4 native SSE / Last-Event-ID / safe event projection ✅
- v5.5 approval/cancel + ETag/If-Match + idempotent command API ✅
- v5.6 Bearer authentication + Principal permissions + tenant derivation + CORS ✅
- v5.7 error model/exception handlers
- v5.8 HTTP tests/dependency overrides/OpenAPI contract
- v5.9 lifespan/health/readiness
- v6.0 production Agent API architecture

## Teaching rule
HTTP convenience must not erase system boundaries. A FastAPI endpoint should not directly run long-lived Agent work merely because it can be declared `async`. Authentication is not authorization; CORS is not either. Optimistic revision, idempotency, durable queueing, Graph replay safety, approval identity, cancellation and event retention remain explicit contracts.