# ELI5 — AI Agent Engineering

Public static learning site for AI Agent engineering, built as an interactive ELI5 course rather than a glossary.

## Completed core tracks

- **Python — 8/8**: data / contracts / project structure / HTTP / async / failure engineering / state / testing.
- **LLM Application Engineering — 10/10**: API lifecycle → context → generation → streaming → structured output → tools → files → routing → evals/safety.
- **RAG Engineering — 10/10**: parsing → chunking → embeddings → ANN/HNSW → BM25/hybrid → rerank → query planning → citation → retrieval/end-to-end eval.
- **Agent Engineering — 10/10**: loop → state/budgets → planning → memory → tools → approval → durability → multi-agent → trajectory eval → production control plane.
- **LangChain / LangGraph — 10/10**: StateGraph → ToolNode → Command/Send → persistence → interrupt → Store → subgraphs → middleware/streaming → production runtime boundaries.
- **FastAPI — 10/10**: Run API → contracts → async/Worker → SSE → idempotent commands → auth/security → errors → testing → lifespan/health → production API architecture.

The core line contains 58 lessons. Roadmaps remain under `docs/`.

## Advanced Agent Engineering — 5/6 live

Advanced material is deliberately compressed into six high-density chapters. Details that can be looked up in framework docs do not become separate lessons.

- **A1 MCP / External Capability Ecosystem ✅** — Host/Client/Server, Tool/Resource/Prompt control ownership, real Python SDK v2 `MCPServer` + `Client`.
- **A2 Browser / Shell / Python / Filesystem Runtime ✅** — run-scoped workspace, browser boundary, constrained shell, separate Python process, artifact lifecycle.
- **A3 Agent Security / Prompt Injection ✅** — trust vs authority, indirect prompt injection, secret isolation, fetch/send scope, exact-action approval.
- **A4 Production Eval / Observability ✅** — layered traces, success/latency/cost metrics, quality eval, failure clustering and regression diagnosis.
- **A5 Distributed / Long-running Agent Runtime ✅** — at-least-once delivery, leases/heartbeats, fencing, stale-worker rejection, checkpoint recovery, backpressure and graceful drain.
- **A6 Agent System Design Capstone** — final design and failure review of a long-running multi-tenant Deep Research Agent.

Full scope: `docs/advanced-agent-roadmap.md`.

## Teaching contract
Every chapter begins with a concrete engineering problem and includes an explorable mechanism, runnable project increment, deliberate failure cases and interview/system-design checks.

## Runnable project

`projects/research-agent-lite/` is the same project across all tracks. Python closed at v1.0, LLM at v2.0, RAG at v3.0, Agent at v4.0, LangGraph at v5.0, FastAPI at v6.0, and Advanced A1–A5 now bring it to **Research Assistant v6.6**.

```bash
cd projects/research-agent-lite
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
uvicorn app.fastapi_app:app --reload
```

Optional real-browser adapter:

```bash
pip install -e ".[browser]"
playwright install chromium
```

Docker, Postgres, Redis, browser runtimes and observability stacks appear only when an engineering problem needs them; they are not standalone syllabus tracks.

## Pages
Deployed with GitHub Actions from the repository root. The static learning UI requires no backend or secret.
