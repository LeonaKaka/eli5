# ELI5 — AI Agent Engineering

Public static learning site for AI Agent engineering, built as an interactive ELI5 course rather than a glossary.

## Current tracks

### Python — 8/8 complete
- 01 Data, references, branching, loops, functions
- 02 Function contracts, type hints, Pydantic, schemas
- 03 Modules, packages, imports, dependency direction
- 04 HTTP, JSON, status codes, API clients
- 05 async / await, event loop, concurrency limits
- 06 exceptions, retry/backoff, logging, fallback, idempotency
- 07 class, dataclass, composition, AgentState
- 08 pytest, mock/fake, runnable Research Agent Lite v1.0

### LLM Application Engineering — 10/10 complete
API lifecycle → conversation state → context → generation → streaming → structured output → tool calling → multimodal/files → routing/reliability → evals/safety.

Full scope: `docs/llm-app-roadmap.md`.

### RAG Engineering — 10/10 complete
Document parsing → chunking → embeddings → ANN/HNSW → BM25/hybrid → reranking → query planning → evidence/citation → retrieval eval → end-to-end RAG eval.

Full scope: `docs/rag-roadmap.md`.

### Agent Engineering — 10/10 complete
Agent loop → state/budgets → planning → memory → tool orchestration → approval → durable execution → multi-agent handoff → trajectory eval → production run architecture.

Full scope: `docs/agent-roadmap.md`.

### LangChain / LangGraph — 8/10 live
- 01 LangChain vs LangGraph / abstraction ladder / `create_agent` vs custom `StateGraph` ✅
- 02 `StateGraph` core / State / Node / Edge / Reducer / conditional routing / compile ✅
- 03 LangChain `@tool` / `ToolNode` / `ToolMessage` / `tools_condition` / Agent Loop ✅
- 04 Conditional Flow / `Command` / `Send` / dynamic fan-out / reducer fan-in ✅
- 05 Persistence / Threads / Checkpointers / `get_state` / history / replay / `update_state` ✅
- 06 `interrupt()` / Human-in-the-loop / `Command(resume=...)` / replay-safe side effects ✅
- 07 Store / namespace / Runtime context / cross-thread long-term memory / write policy ✅
- 08 Subgraphs / shared vs private state / persistence modes / `Command.PARENT` handoff ✅
- 09 Middleware / Streaming / Observability
- 10 Production LangGraph Architecture

Full scope: `docs/langchain-langgraph-roadmap.md`.

## Teaching contract
Every lesson must include:
1. A concrete engineering problem first
2. A visual/explorable explanation
3. Code evolution rather than only final code
4. At least one failure/bug example
5. A continuous project increment
6. Exercises + interview-level checks

## Runnable project

`projects/research-agent-lite/` is the same project across all tracks. Python closed at v1.0, LLM at v2.0, RAG at v3.0, Agent Engineering at v4.0, and the LangChain / LangGraph track now evolves it toward **Research Assistant v5.0**. Current project level: **v4.8**.

```bash
cd projects/research-agent-lite
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

Current framework dependencies track the current major lines used by the lessons: `langchain>=1.3,<2` and `langgraph>=1.2,<2`.

## Current LangChain / LangGraph increments

- v4.1 — first real compiled `StateGraph`
- v4.2 — typed graph state, partial updates, reducers and conditional routing
- v4.3 — real `@tool` + `ToolNode` + correlated `ToolMessage`
- v4.4 — `Command(update + goto)` + `Send` dynamic map-reduce and reducer fan-in
- v4.5 — `InMemorySaver`, `thread_id`, StateSnapshot/history/update-state semantics
- v4.6 — `interrupt()` + `Command(resume=...)`, including an executable unsafe replay example
- v4.7 — real `InMemoryStore`, Runtime context, namespaced cross-thread memory, existing `MemoryWritePolicy` gate and explicit invalidation
- v4.8 — direct shared-state subgraphs, private-state wrapper mapping, subgraph persistence modes and `Command.PARENT` sibling handoff

The migration remains incremental. LangGraph Store does not replace memory policy or tenant authorization. Subgraphs do not justify multi-agent by themselves; shared/private state and handoff context remain explicit contracts. `Command.PARENT` changes graph routing, but does not mean whole specialist histories should be copied across agent boundaries.

`InMemorySaver` and `InMemoryStore` are teaching/test adapters only. Persistent production deployments need durable backends and product-level tenant/run controls.

## Pages
Deployed with GitHub Actions from the repository root. No backend or secret is required for the static learning UI. Lessons 01–08 remain provider-free: they exercise real LangGraph APIs without requiring an external model key.
