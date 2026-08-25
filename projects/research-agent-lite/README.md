# Research Assistant v6.6

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

Python closed at **v1.0**, LLM Application Engineering at **v2.0**, RAG at **v3.0**, Agent Engineering at **v4.0**, LangChain / LangGraph at **v5.0**, FastAPI closed the backend architecture at **v6.0**, and the compressed Advanced Agent Engineering line now extends the same system.

## Advanced increments

- **v6.1–v6.2 / A1 MCP** — capability interoperability: Host/Client/Server, Tool/Resource/Prompt control ownership, real Python SDK v2 `MCPServer` + `Client` discovery/call/read/get.
- **v6.3 / A2 Tool Runtime** — run-scoped workspace, browser adapter, constrained shell runner, separate Python interpreter process and artifact registry.
- **v6.4 / A3 Agent Security** — external-content trust labels, authenticated RunAuthority, fetch/send capability separation, secret isolation, egress scope and exact-action approval.
- **v6.5 / A4 Production Eval / Observability** — layered Run traces, success/latency/cost/token summaries, per-layer Run failure rates, failure clustering and baseline-vs-current regression diagnosis.
- **v6.6 / A5 Distributed Runtime** — at-least-once queue deliveries, worker leases/heartbeats, monotonic fencing tokens, checkpoint takeover, stale-worker rejection, admission control, graceful drain and downstream idempotency/fencing examples.

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

## A2 Tool Runtime boundary

```text
Agent / LangGraph
    │ proposes calls
    ▼
AgentToolRuntime
├── BrowserAdapter
├── AgentWorkspace
├── ShellRunner
├── PythonRunner
└── ArtifactRegistry
    │
    ▼
run-scoped files / processes / deliverables
```

The runtime adds useful guardrails—workspace path checks, `shell=False`, command allowlists, minimal environments, timeouts and bounded output—but it is deliberately **not** called a security sandbox. Strong isolation still belongs to OS/container/VM controls.

## A3 Trust and authority boundary

```text
external Browser / RAG / file content
        ↓
ContextChunk(trust=external_untrusted)
        ↓
LLM proposes ToolIntent
        ↓
AgentSecurityPolicy
├── authenticated RunAuthority
├── capability allowlist
├── network egress scope
└── exact ApprovalGrant
        ↓
ALLOW | DENY | APPROVAL_REQUIRED
```

Untrusted text can influence model reasoning, but it cannot expand product permissions. `READ_SECRET` stays host-only, `NETWORK_FETCH` and `NETWORK_SEND` are separate capabilities, and approval is bound to an immutable exact action snapshot plus an authorized approver.

## A4 Production observability boundary

`production_observability.py` models one Run as layered spans across agent/model/retrieval/tool/runtime/retry/handoff. Batch summaries track success, latency, cost, token use, layer failure rates, failure clusters and quality score. `diagnose(baseline, current)` identifies regressions instead of guessing from final answers.

The deterministic A4 fixture intentionally reproduces:

```text
baseline success = 92%
current success  = 78%
```

with the extra failures concentrated in `tool:search_timeout`. Trace health and quality health remain separate: every operational span may be green while evidence/answer quality drops.

## A5 Distributed ownership model

A queue delivery is not Run ownership. `distributed_runtime.py` adds the missing multi-worker layer:

```text
At-least-once QueueDelivery
        ↓
claim()
        ↓
LeaseGrant
├── worker_id
├── expires_at
├── attempt
└── fencing_token
        ↓
heartbeat / checkpoint / complete
```

Important rules:

- duplicate Queue deliveries are allowed, but only one active lease may own a Run;
- heartbeat extends a live lease but cannot revive an already expired owner;
- the watchdog reaps expired leases and requeues a new attempt from the latest checkpoint;
- takeover increments the fencing token, so a zombie worker with an older token cannot mutate shared state that enforces fencing;
- checkpoint answers **where to resume**, while lease/fence answer **who may resume**;
- admission control rejects new work before global queue depth or per-tenant inflight work becomes unbounded;
- a draining worker may heartbeat/checkpoint/finish current leases but cannot claim new work.

`FencedEffectLedger` demonstrates a downstream that accepts both a monotonic fencing token and an idempotency key. The same idempotency key with the same payload replays the stored result; a stale fence is rejected; reusing a key for a different payload is rejected.

This does **not** create universal exactly-once execution. Many external APIs do not understand fencing tokens. For ambiguous non-idempotent effects, the earlier `DurableActionRunner` rule still applies: reconcile instead of blind replay.

## Current structure

```text
app/
├── distributed_runtime.py        # A5 lease / heartbeat / fence / backpressure
├── production_observability.py   # A4 traces / summaries / regression diagnosis
├── agent_security.py             # A3 trust / capability / approval policy
├── tool_runtime.py               # A2 browser/filesystem/shell/python/artifacts
├── mcp_contracts.py              # A1 primitive/control ownership policy
├── mcp_research_server.py        # A1 MCPServer + research capabilities
├── fastapi_app.py                # HTTP product API / health / SSE / commands
├── fastapi_service.py            # v6 composition root / deployment audit
├── fastapi_worker.py             # separate Worker adapter
├── langgraph_production.py       # control-plane ↔ LangGraph bridge
└── production.py                 # tenant RunStore / Queue / optimistic revisions

tests/
├── test_distributed_runtime.py
├── test_production_observability.py
├── test_agent_security.py
├── test_tool_runtime.py
├── test_mcp_primitives.py
└── ...
```

## Existing ownership boundaries remain intact

- FastAPI owns HTTP/auth/contracts, not long Agent execution.
- RunStore owns product Run truth; Queue delivery is not authoritative state.
- Distributed lease/fencing owns multi-worker execution ownership.
- LangGraph owns graph state/checkpoint/interrupt meaning, not tenant authorization or worker leases.
- MCP standardizes capability interoperability, not capability permission.
- Tool Runtime owns execution mechanics; a stronger sandbox owns hostile-code containment.
- Security policy owns authority decisions outside the model.
- Observability records execution signals; it does not define quality truth or authorization policy.
- External side effects still need real idempotency/fencing/reconciliation contracts.

## Next step

**A6 — Agent System Design Capstone.** No new framework. Design and defend a long-running multi-tenant Deep Research Agent for roughly 1000 concurrent users, combining FastAPI, RunStore, Queue, distributed leases, LangGraph checkpoints, MCP capabilities, Browser/Python sandboxing, approval, security policy, SSE and observability into one coherent production architecture.
