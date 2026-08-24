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

### LangChain / LangGraph — 2/10 live
- 01 LangChain vs LangGraph / abstraction ladder / `create_agent` vs custom `StateGraph` ✅
- 02 `StateGraph` core / State / Node / Edge / Reducer / conditional routing / compile ✅
- 03 LangChain Tools / `ToolNode` / Agent Loop
- 04 Conditional Flow / `Command` / `Send`
- 05 Persistence / Threads / Checkpointers
- 06 Interrupt / Human-in-the-loop / Resume
- 07 Memory / Store
- 08 Subgraphs / Multi-Agent / Handoff
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

`projects/research-agent-lite/` is the same project across all tracks. Python closed at v1.0, LLM at v2.0, RAG at v3.0, Agent Engineering at v4.0, and the LangChain / LangGraph track now evolves it toward **Research Assistant v5.0**. Current project level: **v4.2**.

```bash
cd projects/research-agent-lite
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

Current framework dependencies intentionally track the current major lines used by the lessons: `langchain>=1.3,<2` and `langgraph>=1.2,<2`.

## Current LangChain / LangGraph increments

- v4.1 — first real compiled `StateGraph`, mapping manual Agent concepts onto framework execution without a model provider
- v4.2 — typed graph state, partial node updates, append reducers, fixed edges and conditional routing

The migration is incremental. Existing Tool, RAG, approval, replay-safety, tenant, authorization and evaluation boundaries remain application concerns unless a later lesson explicitly maps them to a framework abstraction.

## Pages
Deployed with GitHub Actions from the repository root. No backend or secret is required for the static learning UI. The runnable project itself now depends on LangChain/LangGraph for the framework track, but the first graph lessons remain model-free and do not require an API key.
