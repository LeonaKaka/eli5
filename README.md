# ELI5 — AI Agent Engineering

Public interactive Chinese learning site for AI Agent engineering, built around one Research Assistant that grows from Python fundamentals into a long-running production-style Agent architecture.

## Completed core tracks

- **Python — 8/8**: data / contracts / project structure / HTTP / async / failure engineering / state / testing.
- **LLM Application Engineering — 10/10**: API lifecycle → context → generation → streaming → structured output → tools → files → routing → evals/safety.
- **RAG Engineering — 10/10**: parsing → chunking → embeddings → ANN/HNSW → BM25/hybrid → rerank → query planning → citation → retrieval/end-to-end eval.
- **Agent Engineering — 10/10**: loop → state/budgets → planning → memory → tools → approval → durability → multi-agent → trajectory eval → production control plane.
- **LangChain / LangGraph — 10/10**: StateGraph → ToolNode → Command/Send → persistence → interrupt → Store → subgraphs → middleware/streaming → production runtime boundaries.
- **FastAPI — 10/10**: Run API → contracts → async/Worker → SSE → idempotent commands → auth/security → errors → testing → lifespan/health → production API architecture.

The core line contains **58 lessons**.

## Advanced Agent Engineering — 6/6 complete

Advanced material is deliberately compressed into six high-density chapters. Details that can be looked up in framework docs do not become standalone courses.

- **A1 MCP / External Capability Ecosystem ✅** — Host/Client/Server, Tool/Resource/Prompt control ownership, real `MCPServer` + `Client`.
- **A2 Browser / Shell / Python / Filesystem Runtime ✅** — run workspace, Browser boundary, constrained Shell, separate Python process, artifact lifecycle.
- **A3 Agent Security / Prompt Injection ✅** — trust vs authority, indirect prompt injection, secret isolation, fetch/send scope and exact-action approval.
- **A4 Production Eval / Observability ✅** — layered traces, success/latency/cost metrics, quality eval, failure clustering and regression diagnosis.
- **A5 Distributed / Long-running Agent Runtime ✅** — at-least-once delivery, leases/heartbeats, fencing, stale-worker rejection, checkpoint recovery, backpressure and graceful drain.
- **A6 Agent System Design Capstone ✅** — final ownership matrix and failure review for a roughly 1,000-concurrent-user, hours-long, multi-tenant Deep Research Agent.

Final advanced roadmap: `docs/advanced-agent-roadmap.md`  
Final system design reference: `docs/agent-system-design-capstone.md`

## Runnable project

`projects/research-agent-lite/` is the same project across all tracks:

```text
Python                  v1.0
LLM Application         v2.0
RAG                     v3.0
Agent Engineering       v4.0
LangGraph               v5.0
FastAPI                 v6.0
Advanced Capstone       v7.0 ✅
```

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

## Final teaching principle

A production Agent design should be defendable by **owner + failure mode + recovery invariant**, not by the number of frameworks in its diagram.

Examples:

```text
Run truth             → RunStore
Delivery              → Queue
Execution ownership   → Lease + Fencing
Graph continuation    → LangGraph Checkpoint
Tool authority        → Host Security Policy
Hostile code          → Sandbox
Client progress       → Event Store / SSE projection
Operational health    → Observability
Quality truth         → Eval
External effects      → Idempotency / Fencing / Reconciliation
```

Docker, Postgres, Redis, Kubernetes, Temporal, cloud providers, sandbox products and observability backends are implementation choices to learn when a real project needs them; they are not missing course tracks.

**Course complete does not mean the default teaching profile is production infrastructure.** The project still intentionally contains in-memory teaching adapters. A real deployment must replace them with shared durable implementations that satisfy the learned contracts.

## Pages

Deployed with GitHub Actions from the repository root. The static learning UI requires no backend or secret.
