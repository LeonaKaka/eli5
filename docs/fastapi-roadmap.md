# FastAPI Roadmap

Scope: expose Research Assistant v5.0 as a real HTTP service without collapsing the durable Agent control-plane boundaries already learned. FastAPI owns HTTP contracts and dependency wiring; it does not replace the RunStore, Queue, Worker, LangGraph runtime, tenant policy or side-effect safety.

Current reference line: FastAPI 0.141.x, Pydantic v2.

Current progress: **10 / 10 complete**, Research Assistant **v6.0**.

## 01 — API Boundary / ASGI / First Run API ✅
Build the first real service around the existing product run lifecycle. Understand ASGI request/response boundaries, `FastAPI()`, path operations, `POST /runs`, `GET /runs/{run_id}`, 201/200/404 semantics and automatic OpenAPI. The HTTP request only submits work; it does not execute a long Agent run inline.

## 02 — Pydantic Contracts / Depends / Tenant Context ✅
Use explicit request/response models, `Annotated + Depends`, dependency-derived request context and response filtering. Keep internal fields such as tenant identifiers, checkpoint ids and budgets out of the public response model. The temporary client-supplied tenant header from this lesson is explicitly replaced by authenticated identity in lesson 06.

## 03 — Async Boundary / Worker Separation ✅
Understand `async def`, blocking I/O, FastAPI threadpool behavior and why async syntax is not a background-job system. Keep long Agent execution behind Queue/Worker. Short blocking adapters may use explicit thread offload; `BackgroundTasks` is not presented as durable multi-worker execution.

## 04 — SSE Streaming ✅
Expose `/runs/{run_id}/stream` with native `EventSourceResponse` / `ServerSentEvent`. Use stable client-safe event types, sequence ids, `Last-Event-ID` replay, disconnect awareness and bounded retention. A retention gap is explicit rather than silently dropping history; raw Graph/debug/control-plane state is never the public stream schema.

## 05 — Approval / Cancel / Idempotent Commands ✅
Add exact approval and cancellation command endpoints. Public Run responses expose a revision ETag; mutating commands require strong `If-Match` preconditions plus `Idempotency-Key`. Same-key/same-command retries replay the original response without a second RESUME; key reuse with a different command is 409; stale revisions are 412 and missing preconditions are 428.

## 06 — Auth / Security / CORS / Trusted Boundaries ✅
Replace trusted `X-Tenant-ID` with Bearer authentication. A token becomes a `Principal(subject, tenant_id, permissions)`; route dependencies enforce `runs:read/create/approve/cancel`, and resource scope uses the tenant derived from authenticated identity. Add explicit credentialed CORS and separate proxy/header trust from application identity.

## 07 — Errors / Exception Handlers / Problem Details ✅
Install a stable `ProblemDetails` public error contract across request validation, authentication/authorization, not-found, conflict/precondition and unexpected server errors. Generate a server request id and expose it in both response header/body for private-log correlation. Preserve protocol-significant headers such as `WWW-Authenticate`, and never echo raw request bodies, stack traces, checkpoint state or exception text in generic 500 responses. Document error models in path-operation `responses=` as well as handling them at runtime.

## 08 — Testing / Dependency Overrides / OpenAPI Contract ✅
Use `TestClient`, `app.dependency_overrides`, fake Principal/control-plane adapters and selective OpenAPI assertions. Separate endpoint-unit tests from integration tests: unit tests may replace auth/external adapters, while revision/Queue/LangGraph behavior remains real in integration tests when those are the mechanisms under test. Contract tests lock Bearer security, command headers, ProblemDetails and important response codes without snapshotting irrelevant generated OpenAPI noise.

## 09 — Lifespan / Health / Readiness / Resource Management ✅
Own long-lived process resources through FastAPI lifespan rather than request handlers or import-time globals. Keep liveness independent from transient external dependency failures, make readiness reflect required service dependencies, allow optional degraded dependencies, and clean up already-started resources if startup fails partway through. Add public minimal `/health/live` and `/health/ready` operational probes.

## 10 — Production Agent API Architecture ✅
Close Research Assistant at v6.0: API → auth/dependencies → RunStore → Queue/Workers → LangGraph → Stream/HITL. Add one composition root and a deployment-profile audit that permits deterministic in-memory adapters in teaching mode but rejects them when the caller claims production. Production deployment still requires external durable Run storage, queueing, graph checkpoints, retained events, atomic idempotency storage, real identity validation and durable approval metadata; those infrastructure replacements continue in the Docker/deployment track.

## Project evolution
Continue `projects/research-agent-lite/` from Research Assistant v5.0:
- v5.1 first FastAPI application + POST/GET Run endpoints ✅
- v5.2 Pydantic public contracts + dependency boundary ✅
- v5.3 async request / worker lifetime separation ✅
- v5.4 native SSE / Last-Event-ID / safe event projection ✅
- v5.5 approval/cancel + ETag/If-Match + idempotent command API ✅
- v5.6 Bearer authentication + Principal permissions + tenant derivation + CORS ✅
- v5.7 ProblemDetails + exception handlers + request correlation ✅
- v5.8 dependency overrides + layered HTTP/integration/OpenAPI contract tests ✅
- v5.9 lifespan/resource ownership + liveness/readiness ✅
- v6.0 production Agent API composition + deployment profile gate ✅

## Teaching rule
HTTP convenience must not erase system boundaries. A FastAPI endpoint should not directly run long-lived Agent work merely because it can be declared `async`. Authentication is not authorization; CORS is not either. Uniform error JSON must not erase meaningful HTTP status codes, fast tests must not mock away the concurrency/recovery mechanisms they are supposed to verify, and a process that can start inside Docker must not be mislabeled production-ready while its authoritative state is still process-local.
