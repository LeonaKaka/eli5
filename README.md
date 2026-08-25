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

## Advanced Agent Engineering — 2/6 live

Advanced material is deliberately compressed into six high-density chapters. Details that can be looked up in framework docs do not become separate lessons.

- **A1 MCP / External Capability Ecosystem ✅** — the existing two MCP pages form one chapter: Host/Client/Server, Tool/Resource/Prompt control ownership, real Python SDK v2 `MCPServer` + `Client`. Transport/OAuth/protocol minutiae are introduced only when later work needs them.
- **A2 Browser / Shell / Python / Filesystem Runtime ✅** — run-scoped workspace, real-browser adapter boundary, constrained shell, separate Python process, artifact registry, and one complete browser → source → generated code → artifact flow.
- **A3 Agent Security / Prompt Injection** — attack A2 with untrusted browser/RAG/file content, secret access, path/network escape and capability abuse.
- **A4 Production Eval / Observability** — diagnose quality drops across model/retrieval/tool/runtime traces, regression sets and failure clusters.
- **A5 Distributed / Long-running Agent Runtime** — leases, heartbeat, duplicate delivery, stale workers, backpressure, recovery and side-effect idempotency.
- **A6 Agent System Design Capstone** — design and defend a long-running multi-tenant Deep Research Agent architecture.

Full scope: `docs/advanced-agent-roadmap.md`. The old `docs/mcp-roadmap.md` now records A1 as complete rather than a 10-lesson subtrack.

## Teaching contract
Every chapter begins with a concrete engineering problem and includes an explorable mechanism, runnable project increment, deliberate failure cases and interview/system-design checks.

## Runnable project

`projects/research-agent-lite/` is the same project across all tracks. Python closed at v1.0, LLM at v2.0, RAG at v3.0, Agent at v4.0, LangGraph at v5.0, FastAPI at v6.0, A1 MCP at v6.2, and A2 Tool Runtime now brings it to **Research Assistant v6.3**.

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

Docker, Postgres, Redis, browser runtimes and observability stacks are used when later chapters need them; they are not standalone syllabus tracks.

## Pages
Deployed with GitHub Actions from the repository root. The static learning UI requires no backend or secret.
