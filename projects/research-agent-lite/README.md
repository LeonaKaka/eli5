# Research Assistant v6.2

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

Python closed at **v1.0**, LLM Application Engineering at **v2.0**, RAG at **v3.0**, Agent Engineering at **v4.0**, LangChain / LangGraph at **v5.0**, FastAPI closed the backend architecture at **v6.0**, and the advanced MCP / Tool Ecosystem track now evolves the same system beyond an application-local tool registry.

## MCP increments

- **v6.1** — explicit MCP primitive/control model: Tool=model-controlled capability, Resource=application-controlled addressed context, Prompt=user-controlled reusable workflow.
- **v6.2** — real Python SDK v2 `MCPServer` plus first-class `Client`; provider-free paper-search Tool, concrete/template Resources, Prompt and in-process MCP regression tests.

Current MCP reference line used by the course: specification **2026-07-28**, Python SDK `mcp>=2,<3`.

## Run teaching profile

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
uvicorn app.fastapi_app:app --reload
```

The Research MCP server can also be run over Streamable HTTP:

```bash
python -m app.mcp_research_server
```

The code intentionally tests MCP in-process first:

```python
from mcp import Client
from app.mcp_research_server import mcp

async with Client(mcp) as client:
    tools = await client.list_tools()
    result = await client.call_tool("search_papers", {"query": "domain wall"})
```

`Client(mcp)` still exercises the real MCP capability surface but removes subprocess/network noise from the test. Later lessons add stdio and Streamable HTTP explicitly.

## Current MCP surface

```text
Tool
  search_papers(query, limit)

Resource
  research://catalog

Resource Template
  research://paper/{paper_id}

Prompt
  compare_papers(left_id, right_id)
```

The server is deliberately provider-free. Tool names/descriptions/input schemas are generated from Python functions, docstrings and type hints by `MCPServer`; clients discover them with MCP rather than importing an application-private function registry.

## Current structure

```text
app/
├── mcp_contracts.py              # primitive/control ownership policy
├── mcp_research_server.py        # MCPServer + research Tool/Resources/Prompt
├── fastapi_app.py                # HTTP product API / health / SSE / commands
├── fastapi_service.py            # v6 composition root / deployment audit
├── fastapi_security.py           # Bearer / Principal / permissions
├── fastapi_errors.py             # ProblemDetails / request correlation
├── fastapi_worker.py             # separate Worker adapter
├── langgraph_production.py       # product control-plane ↔ LangGraph bridge
└── production.py                 # tenant RunStore / Queue / optimistic revisions

tests/
├── test_mcp_primitives.py
├── test_fastapi_lifecycle_production.py
└── ...
```

## MCP does not replace the existing runtime

```text
Host / Research Assistant
  LLM · LangGraph · tenant · permissions · approval · UI
        │
        └─ MCP Client(s)
             │
             └─ MCP Server(s)
                  Tools · Resources · Prompts
```

The server advertising a tool does **not** grant the current model permission to use it. The Host still decides which discovered capabilities are exposed for a tenant/run, whether an action needs human approval, and how tool side effects are made replay-safe.

Likewise:

- MCP does not replace LangGraph state/checkpoints/interrupts.
- MCP Resources are not automatically trusted context.
- MCP transport/session semantics do not replace RunStore/Queue durability.
- Tool input schema does not replace authorization or downstream idempotency.

## Existing v6.0 backend remains intact

The public API still exposes:

```text
GET  /health/live
GET  /health/ready
POST /runs
GET  /runs/{run_id}
GET  /runs/{run_id}/stream
POST /runs/{run_id}/approvals/{approval_request_id}
POST /runs/{run_id}/cancel
```

FastAPI owns HTTP contracts/auth; the product control-plane owns tenant/run/revision/commands; Queue/Workers own durable execution; LangGraph owns graph state/checkpoints/interrupt/resume semantics. MCP is being added as a capability interoperability layer, not as a replacement for any of those responsibilities.

## Next step

MCP 03–04: move the same capability server across **in-process → stdio → Streamable HTTP**, learn the 2026 stateless protocol boundary, then harden model-facing Tool contracts, structured results, errors and progress.
