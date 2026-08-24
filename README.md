# ELI5 — AI Agent Engineering

Public static learning site for AI Agent engineering, built as an interactive ELI5 course rather than a glossary.

## Current tracks

### Python — 8/8 complete
Data / contracts / project structure / HTTP / async / failure engineering / state / testing.

### LLM Application Engineering — 10/10 complete
API lifecycle → conversation state → context → generation → streaming → structured output → tool calling → multimodal/files → routing/reliability → evals/safety.

Full scope: `docs/llm-app-roadmap.md`.

### RAG Engineering — 10/10 complete
Document parsing → chunking → embeddings → ANN/HNSW → BM25/hybrid → reranking → query planning → evidence/citation → retrieval eval → end-to-end RAG eval.

Full scope: `docs/rag-roadmap.md`.

### Agent Engineering — 10/10 complete
Agent loop → state/budgets → planning → memory → tool orchestration → approval → durable execution → multi-agent handoff → trajectory eval → production run architecture.

Full scope: `docs/agent-roadmap.md`.

### LangChain / LangGraph — 10/10 complete
StateGraph → ToolNode → Command/Send → persistence → interrupt/resume → Store → subgraphs/handoffs → middleware/streaming → production runtime boundaries.

Full scope: `docs/langchain-langgraph-roadmap.md`.

### FastAPI — 10/10 complete
- 01 API boundary / Run resources / OpenAPI ✅
- 02 Pydantic contracts / dependencies / response filtering ✅
- 03 async boundary / blocking SDK / durable Worker separation ✅
- 04 native SSE / reconnect / retention / safe projection ✅
- 05 approval / cancel / ETag / `If-Match` / `Idempotency-Key` ✅
- 06 Bearer / Principal permissions / tenant scope / CORS / proxy trust ✅
- 07 ProblemDetails / exception handlers / request correlation / safe 500s ✅
- 08 TestClient / dependency overrides / integration vs unit / OpenAPI contract ✅
- 09 Lifespan / resource ownership / liveness / readiness ✅
- 10 Production Agent API composition / deployment profile audit ✅

Full scope: `docs/fastapi-roadmap.md`.

### Docker / Deployment — next
Containerize the v6.0 API and Worker separately, externalize process-local durable adapters, wire service networking/config/secrets/volumes, and validate restart/multi-replica behavior.

## Teaching contract
Every lesson must include a concrete engineering problem, visual/explorable explanation, code evolution, at least one failure case, a continuous project increment, and interview-level checks.

## Runnable project

`projects/research-agent-lite/` is the same project across all tracks. Python closed at v1.0, LLM at v2.0, RAG at v3.0, Agent Engineering at v4.0, LangChain / LangGraph at v5.0, and FastAPI closes the backend architecture at **Research Assistant v6.0**.

```bash
cd projects/research-agent-lite
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
uvicorn app.fastapi_app:app --reload
```

Current framework/service dependencies follow the course reference lines: `langchain>=1.3,<2`, `langgraph>=1.2,<2`, `fastapi[standard]>=0.141,<1`.

## FastAPI project evolution

- v5.1 — Run resource API
- v5.2 — request/response contracts and dependency boundaries
- v5.3 — HTTP request lifetime separated from Worker lifetime
- v5.4 — native SSE + safe event projection + replay/retention
- v5.5 — ETag/If-Match + idempotent approval/cancel commands
- v5.6 — Bearer Principal / permissions / tenant derivation / CORS
- v5.7 — ProblemDetails + exception handlers + request correlation
- v5.8 — dependency overrides + layered HTTP/integration/OpenAPI contract tests
- v5.9 — lifespan/resource ownership + liveness/readiness
- v6.0 — final service composition + production deployment audit

The API preserves the earlier durable architecture: FastAPI owns HTTP contracts; product control-plane owns tenant/run/revision/commands; Queue/Workers own durable execution; LangGraph owns Graph state/checkpoints/interrupts. The v6.0 teaching profile remains deliberately process-local and runnable; declaring a production profile while keeping process-local RunStore/Queue/checkpointer/event/idempotency/auth metadata is rejected rather than mislabeled production-ready.

## What remains after FastAPI

The original core job-skill sequence still has one major implementation track left: **Docker / deployment**. Vector DB was already integrated deeply into the RAG track, and evaluation has been integrated throughout LLM/RAG/Agent rather than postponed to one isolated course. After Docker, the original core roadmap is essentially complete; further tracks would be extensions such as Postgres/Redis/message queues, Kubernetes/cloud, observability, or framework-specific production infrastructure rather than missing fundamentals.

## Pages
Deployed with GitHub Actions from the repository root. The static learning UI requires no backend or secret.
