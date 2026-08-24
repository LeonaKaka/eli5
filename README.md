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

### FastAPI — 6/10 live
- 01 API boundary / ASGI / `POST /runs` / `GET /runs/{id}` / OpenAPI ✅
- 02 Pydantic contracts / dependencies / response filtering ✅
- 03 async boundary / blocking SDK / threadpool / durable Worker separation ✅
- 04 native SSE / `Last-Event-ID` / reconnect / retention / safe event projection ✅
- 05 approval / cancel / ETag / `If-Match` / `Idempotency-Key` ✅
- 06 Bearer authentication / Principal permissions / tenant derivation / CORS / proxy trust ✅
- 07 Errors / Exception handlers
- 08 Testing / Dependency overrides / OpenAPI contract
- 09 Lifespan / Health / Readiness
- 10 Production Agent API Architecture

Full scope: `docs/fastapi-roadmap.md`.

## Teaching contract
Every lesson must include a concrete engineering problem, visual/explorable explanation, code evolution, at least one failure case, a continuous project increment, and interview-level checks.

## Runnable project

`projects/research-agent-lite/` is the same project across all tracks. Python closed at v1.0, LLM at v2.0, RAG at v3.0, Agent Engineering at v4.0, LangChain / LangGraph at v5.0, and FastAPI now evolves it toward **Research Assistant v6.0**. Current level: **v5.6**.

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

- v5.1 — first FastAPI Run resource API
- v5.2 — request/response contracts and dependency boundaries
- v5.3 — HTTP request lifetime separated from durable Worker lifetime
- v5.4 — native SSE + safe Run event projection + Last-Event-ID replay
- v5.5 — approval/cancel commands use ETag/If-Match and atomic teaching idempotency registry
- v5.6 — Bearer authentication derives Principal/tenant; route permissions, explicit credentialed CORS and proxy trust boundaries

The API now derives tenant scope from authenticated identity instead of trusting `X-Tenant-ID`. Demo bearer tokens are provider-free teaching credentials only; production must validate real identity-provider/session/API-key material. CORS is configured as a browser-origin policy and is not treated as authorization.

Mutating commands require both optimistic revision preconditions and idempotency keys. The in-memory idempotency/event/auth adapters exist for deterministic teaching; multi-replica production needs durable shared implementations and atomic command reservation.

## Pages
Deployed with GitHub Actions from the repository root. The static learning UI requires no backend or secret.
