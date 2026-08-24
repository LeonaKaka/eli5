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

### FastAPI — 2/10 live
- 01 API boundary / ASGI / `POST /runs` / `GET /runs/{id}` / 201 / 404 / OpenAPI ✅
- 02 Pydantic contracts / `Annotated + Depends` / tenant context / response filtering ✅
- 03 Async boundary / Worker separation
- 04 SSE streaming
- 05 Approval / Cancel / Idempotent commands
- 06 Auth / Security / CORS
- 07 Errors / Exception handlers
- 08 Testing / Dependency overrides / OpenAPI contract
- 09 Lifespan / Health / Readiness
- 10 Production Agent API Architecture

Full scope: `docs/fastapi-roadmap.md`.

## Teaching contract
Every lesson must include a concrete engineering problem, visual/explorable explanation, code evolution, at least one failure case, a continuous project increment, and interview-level checks.

## Runnable project

`projects/research-agent-lite/` is the same project across all tracks. Python closed at v1.0, LLM at v2.0, RAG at v3.0, Agent Engineering at v4.0, LangChain / LangGraph at v5.0, and FastAPI now evolves it toward **Research Assistant v6.0**. Current level: **v5.2**.

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

- v5.1 — first real FastAPI application; `POST /runs` creates/enqueues a Run and `GET /runs/{run_id}` reads it
- v5.2 — explicit request/response Pydantic models, tenant/runtime dependencies, anti-enumeration lookup and public response filtering

The HTTP layer deliberately preserves the existing architecture: request lifetime is not Agent-run lifetime. Creating a Run does not execute the long Agent inline; Queue/Worker/LangGraph remain separate. The current `X-Tenant-ID` dependency is a teaching input only and is not presented as production authentication.

## Pages
Deployed with GitHub Actions from the repository root. The static learning UI requires no backend or secret.
