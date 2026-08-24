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
- 01 abstraction ladder / `create_agent` vs custom `StateGraph` ✅
- 02 State / Node / Edge / Reducer / compile ✅
- 03 `@tool` / `ToolNode` / `ToolMessage` / `tools_condition` ✅
- 04 `Command` / `Send` / dynamic fan-out / reducer fan-in ✅
- 05 thread / checkpointer / StateSnapshot / history / replay ✅
- 06 `interrupt()` / HITL / `Command(resume=...)` / replay-safe side effects ✅
- 07 Store / Runtime context / namespaced cross-thread memory / write policy ✅
- 08 shared/private subgraphs / persistence modes / `Command.PARENT` handoff ✅
- 09 LangChain middleware / LangGraph v2 streaming / observability ✅
- 10 production LangGraph architecture / product-control boundaries ✅

Full scope: `docs/langchain-langgraph-roadmap.md`.

## Teaching contract
Every lesson must include a concrete engineering problem, visual/explorable explanation, code evolution, at least one failure case, a continuous project increment, and interview-level checks.

## Runnable project

`projects/research-agent-lite/` is the same project across all tracks. Python closed at v1.0, LLM at v2.0, RAG at v3.0, Agent Engineering at v4.0, and LangChain / LangGraph now closes at **Research Assistant v5.0**.

```bash
cd projects/research-agent-lite
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

Framework dependencies track the course reference line: `langchain>=1.3,<2` and `langgraph>=1.2,<2`.

## LangGraph project evolution

- v4.1 — first compiled `StateGraph`
- v4.2 — typed state, partial updates, reducers, conditional routing
- v4.3 — real ToolNode / ToolMessage loop
- v4.4 — Command + Send dynamic orchestration
- v4.5 — checkpointer / thread / checkpoint history
- v4.6 — interrupt / durable resume
- v4.7 — Store / Runtime context / memory policy
- v4.8 — subgraphs / private state / parent handoff
- v4.9 — real AgentMiddleware hook contract + LangGraph v2 updates/values/custom stream
- v5.0 — `ProductionGraphBridge`, joining LangGraph checkpoints/interrupts with tenant-scoped RunStore, Queue, optimistic worker revisions, approval authorization and cancellation

The final architecture deliberately keeps three layers distinct:

1. **LangGraph runtime** — graph state, routing, checkpoint, interrupt, Store, subgraph, streaming.
2. **Application control plane** — tenant, product run status, revision, approval authorization, cancellation, ownership and business policy.
3. **Infrastructure** — durable databases/checkpointers/stores, queue/broker, worker lease/heartbeat, secrets, scaling and telemetry backend.

A `thread_id` is not an authorization token. A checkpoint does not replace queue/worker CAS. An interrupt does not replace approval policy. Framework orchestration does not remove side-effect idempotency or replay-safety requirements.

## Pages
Deployed with GitHub Actions from the repository root. The static learning UI requires no backend or secret. The framework lessons remain provider-free by using deterministic graph/model boundaries where possible.

## Next track
FastAPI: expose the existing v5.0 Run / status / streaming / approval / cancel lifecycle as a real service instead of starting from toy endpoints.
