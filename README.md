# ELI5 — AI Agent Engineering

Public static learning site for AI Agent engineering, built as an interactive ELI5 course rather than a glossary.

## Completed core tracks

- **Python — 8/8**: data / contracts / project structure / HTTP / async / failure engineering / state / testing.
- **LLM Application Engineering — 10/10**: API lifecycle → context → generation → streaming → structured output → tools → files → routing → evals/safety.
- **RAG Engineering — 10/10**: parsing → chunking → embeddings → ANN/HNSW → BM25/hybrid → rerank → query planning → citation → retrieval/end-to-end eval.
- **Agent Engineering — 10/10**: loop → state/budgets → planning → memory → tools → approval → durability → multi-agent → trajectory eval → production control plane.
- **LangChain / LangGraph — 10/10**: StateGraph → ToolNode → Command/Send → persistence → interrupt → Store → subgraphs → middleware/streaming → production runtime boundaries.
- **FastAPI — 10/10**: Run API → contracts → async/Worker → SSE → idempotent commands → auth/security → errors → testing → lifespan/health → production API architecture.

Roadmaps: `docs/llm-app-roadmap.md`, `docs/rag-roadmap.md`, `docs/agent-roadmap.md`, `docs/langchain-langgraph-roadmap.md`, `docs/fastapi-roadmap.md`.

## Advanced track — MCP / Tool Ecosystem — 2/10 live

- 01 Host / Client / Server / Tools / Resources / Prompts / control ownership ✅
- 02 Python SDK v2 `MCPServer` + first-class `Client` / real discovery/call/read/get ✅
- 03 stdio / Streamable HTTP / 2026 stateless MCP
- 04 tool contracts / structured results / errors / progress
- 05 resources / templates / cache / subscriptions
- 06 prompts / completions / user workflows
- 07 multi-server discovery / namespacing / routing
- 08 OAuth / authorization / trust
- 09 MCP ↔ LangGraph / gateway / observability
- 10 production MCP ecosystem / Tasks / extensions

Full scope: `docs/mcp-roadmap.md`.

## Teaching contract
Every lesson begins with a concrete engineering problem and includes visual/explorable mechanism, code evolution, deliberate failure cases, one continuous Research Assistant project increment, and interview-level checks.

## Runnable project

`projects/research-agent-lite/` is the same project across all tracks. Python closed at v1.0, LLM at v2.0, RAG at v3.0, Agent at v4.0, LangGraph at v5.0, FastAPI at v6.0, and MCP now evolves it at **Research Assistant v6.2**.

```bash
cd projects/research-agent-lite
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
uvicorn app.fastapi_app:app --reload
```

Current framework lines include `langchain>=1.3,<2`, `langgraph>=1.2,<2`, `fastapi[standard]>=0.141,<1`, and current MCP Python SDK v2 `mcp>=2,<3`.

## What comes after MCP

Docker is no longer treated as a standalone teaching track; containerization will appear when a later exercise actually needs deployment/isolation. The advanced main line is:

```text
MCP / Tool Ecosystem
→ Browser / Shell / Code Sandbox Agent
→ Agent Security / Prompt Injection
→ Production Eval / Observability
→ Distributed / Long-running Agent Runtime
→ Agent System Design / Capstone
```

Optional specialist topics can follow: self-hosted model inference, Kubernetes/cloud, GraphRAG/knowledge graphs, realtime/voice, computer-use GUI agents, CI/CD and deeper observability stacks.

## Pages
Deployed with GitHub Actions from the repository root. The static learning UI requires no backend or secret.
