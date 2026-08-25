# Research Assistant v7.0

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

Python closed at **v1.0**, LLM Application Engineering at **v2.0**, RAG at **v3.0**, Agent Engineering at **v4.0**, LangChain / LangGraph at **v5.0**, FastAPI at **v6.0**, and the compressed Advanced Agent Engineering line closes at **v7.0**.

## Advanced increments

- **v6.1–v6.2 / A1 MCP** — Host/Client/Server capability interoperability, Tool/Resource/Prompt control ownership, real `MCPServer` + `Client`.
- **v6.3 / A2 Tool Runtime** — run-scoped workspace, Browser adapter, constrained Shell, separate Python interpreter and artifact registry.
- **v6.4 / A3 Agent Security** — trust vs authority, secret isolation, fetch/send capability split, egress scope and exact-action approval.
- **v6.5 / A4 Eval / Observability** — layered traces, success/latency/cost/token summaries, failure clustering and baseline-vs-current regression diagnosis.
- **v6.6 / A5 Distributed Runtime** — at-least-once delivery, leases/heartbeats, fencing, checkpoint takeover, backpressure and graceful drain.
- **v7.0 / A6 System Design Capstone** — final ownership matrix, architecture validator and failure drills spanning the entire long-running multi-tenant Agent system.

## Run teaching profile

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
uvicorn app.fastapi_app:app --reload
```

Optional real-browser support:

```bash
pip install -e ".[browser]"
playwright install chromium
```

## Final v7.0 architecture

```text
Client
  ↓
FastAPI × N
  ├─ identity / auth
  ├─ HTTP contracts
  ├─ commands / approval
  └─ admission / quotas
  ↓
RunStore  ← authoritative product Run truth
  ├─ Event Store → SSE projection / replay
  └─ Queue → at-least-once delivery
             ↓
      Distributed Workers × N
      lease / heartbeat / fence / drain
             ↓
          LangGraph
      checkpoint / interrupt / resume
             ↓
   RAG / MCP / Tool Runtime / Sandbox
             ↓
   Security Policy / exact HITL approval
             ↓
       External systems
   idempotency / fencing / reconcile

Cross-cutting:
Object Storage · Observability · Eval · Audit
```

## Final ownership contract

`app/capstone_architecture.py` makes the final architecture machine-reviewable:

```text
Identity                 → Identity Provider
Run truth                → RunStore
Delivery                 → Queue
Execution ownership      → Lease Coordinator
Graph continuation       → LangGraph Checkpointer
Tool authority           → Security Policy
Hostile-code isolation   → Sandbox
Artifacts                → Object Store
Client events            → Event Store
Operational telemetry    → Observability Pipeline
Quality truth            → Eval Pipeline
Side-effect safety       → Idempotency / Reconciliation contract
```

`CapstoneArchitectureReviewer` rejects designs that confuse those responsibilities, even if the architecture diagram looks sophisticated.

Examples that fail review:

```text
LangGraph checkpoint = RunStore        ❌
Queue pop = Worker ownership           ❌
LLM = Tool permission owner            ❌
SSE event log = authoritative state    ❌
same-user subprocess = security sandbox ❌
no tenant/CAS/fencing/backpressure     ❌
```

## Final failure drills

`failure_drill()` covers eight end-to-end scenarios:

```text
Worker crash / zombie takeover
Duplicate Queue delivery
Malicious Browser/RAG/file content
Model / quality regression
SSE disconnect
RunStore outage
Ambiguous external side effect
Traffic overload
```

Each drill is expressed as:

```text
Detect
→ Contain
→ Recover
→ preserve one explicit invariant
```

Examples:

- Worker crash: lease expires → new Worker resumes latest checkpoint with a higher fence → zombie writes are rejected.
- Malicious page: external content stays untrusted → RunAuthority cannot expand through prompt text → exact approval/sandbox protects high-risk execution.
- SSE disconnect: Run continues → replay after `Last-Event-ID` → retention gap falls back to authoritative Run truth.
- Ambiguous side effect: never blind-retry a non-idempotent `IN_FLIGHT` action; reuse committed state, replay only under a real idempotency contract, otherwise reconcile.
- RunStore outage: readiness fails and state-changing work stops rather than inventing product state from Queue/checkpoint fragments.
- Overload: finite global/per-tenant admission limits reject or defer work before the queue and downstream systems collapse.

## Existing boundaries from earlier versions remain part of v7.0

- **FastAPI** owns HTTP/auth/contracts, not hours-long Agent execution.
- **RunStore** owns product Run truth; Queue delivery is not authoritative state.
- **Lease/fencing** owns multi-worker execution authority; checkpoint does not.
- **LangGraph** owns graph state/checkpoint/interrupt semantics, not tenant authorization.
- **MCP** standardizes capability interoperability, not capability permission.
- **Tool Runtime** owns execution mechanics; a real sandbox owns hostile-code containment.
- **Security Policy** keeps authority outside the model and untrusted content.
- **Observability** explains execution health; **Eval** defines quality evidence.
- **SSE/Event Store** is a client projection that can be rebuilt from Run truth.
- **External effects** still need real idempotency/fencing/reconciliation contracts; the project never claims magical end-to-end exactly-once execution.

## Current structure

```text
app/
├── capstone_architecture.py      # v7 final ownership validator / failure drills
├── distributed_runtime.py       # A5 lease / heartbeat / fence / backpressure
├── production_observability.py  # A4 trace / metrics / regression diagnosis
├── agent_security.py            # A3 trust / capability / approval policy
├── tool_runtime.py              # A2 Browser/filesystem/Shell/Python/artifacts
├── mcp_contracts.py             # A1 primitive/control ownership
├── mcp_research_server.py       # A1 MCP capabilities
├── fastapi_app.py               # product HTTP API / SSE / commands
├── fastapi_service.py           # composition root / deployment audit
├── langgraph_production.py      # product control ↔ LangGraph bridge
└── production.py                # RunStore / Queue / revisions

tests/
├── test_capstone_architecture.py
├── test_distributed_runtime.py
├── test_production_observability.py
├── test_agent_security.py
├── test_tool_runtime.py
└── ...
```

Final architecture reference: `../../docs/agent-system-design-capstone.md`.

## Course complete — but teaching profile is still teaching infrastructure

**v7.0 means the Agent-engineering architecture/learning line is complete. It does not mean the default in-memory teaching adapters suddenly became production infrastructure.**

A real deployment still has to provide shared durable implementations for Run state, Queue/coordination, checkpoints, events, idempotency, identity, artifacts and sandbox execution. Docker, Postgres, Redis, Temporal, Kubernetes, cloud runtimes or other products are implementation choices to evaluate against these contracts when the project actually needs them.
