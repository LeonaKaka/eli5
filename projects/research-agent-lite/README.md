# Research Assistant v6.5

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

Python closed at **v1.0**, LLM Application Engineering at **v2.0**, RAG at **v3.0**, Agent Engineering at **v4.0**, LangChain / LangGraph at **v5.0**, FastAPI closed the backend architecture at **v6.0**, and the compressed Advanced Agent Engineering line now extends the same system.

## Advanced increments

- **v6.1–v6.2 / A1 MCP** — capability interoperability: Host/Client/Server, Tool/Resource/Prompt control ownership, real Python SDK v2 `MCPServer` + `Client` discovery/call/read/get.
- **v6.3 / A2 Tool Runtime** — run-scoped workspace, browser adapter, constrained shell runner, separate Python interpreter process and artifact registry.
- **v6.4 / A3 Agent Security** — external-content trust labels, authenticated RunAuthority, fetch/send capability separation, secret isolation, egress scope and exact-action approval.
- **v6.5 / A4 Production Eval / Observability** — layered Run traces, success/latency/cost/token summaries, per-layer Run failure rates, normalized failure clustering, baseline-vs-current regression diagnosis and explicit separation between operational telemetry and quality evaluation.

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

Prompt injection is treated as an authority-confusion problem rather than a string-filtering problem.

```text
Browser / RAG / file / tool output
        │
        ▼
ContextChunk(trust=external_untrusted)
        │
        ▼
LLM proposes ToolIntent
        │
        ▼
AgentSecurityPolicy
├── authenticated RunAuthority
├── capability allowlist
├── network egress host scope
├── external-content taint
└── exact ApprovalGrant
        │
        ▼
ALLOW | DENY | APPROVAL_REQUIRED
```

Untrusted text can influence model reasoning, but it cannot expand product permissions. `READ_SECRET` stays host-only, `NETWORK_FETCH` and `NETWORK_SEND` are separate capabilities, and approval is bound to an immutable exact action snapshot plus an authorized approver.

## A4 Production observability boundary

A final success score is not enough to debug an Agent. `production_observability.py` models one Run as layered operational spans:

```text
RunTrace
├── agent
├── model
├── retrieval
├── tool
├── runtime
├── retry
└── handoff
```

Each `RunSpan` carries compact operational attributes such as duration, status, error type, model/tool name, token counts and cost. The teaching model intentionally does **not** make raw prompts, completions, retrieved documents or tool payloads part of the default trace contract; those may contain PII, secrets, customer data or prompt-injection content and should be opt-in/redacted telemetry.

`ProductionRunAnalyzer.summarize()` produces:

```text
success_rate
average_latency_ms
average_cost_usd
average_tokens
layer_failure_rates
failure_clusters
average_quality_score
```

Layer failure rates count affected **Runs**, not the number of error spans. A Run that retries the same broken tool five times still represents one affected Run for the layer-rate metric.

`ProductionRunAnalyzer.diagnose(baseline, current)` compares two traffic/eval batches and reports:

```text
success delta
latency ratio
cost ratio
quality delta
per-layer failure deltas
top normalized failure clusters
suspected regression layers
```

The deterministic A4 fixture intentionally reproduces:

```text
baseline success = 92%
current success  = 78%
```

with the additional failures concentrated in `tool:search_timeout`. The correct diagnosis is therefore a Tool-layer regression (plus latency/quality consequences), not merely “success dropped 14 percentage points.”

## Trace health is not quality health

Operational telemetry and quality evaluation remain separate:

```text
Metrics
  when/how much did the system change?

Trace
  where in one Run did execution change/fail?

Eval
  was the answer/evidence/trajectory actually good?

Audit
  who authorized or performed a sensitive action?
```

All model/tool calls can return 200 while retrieval evidence or answer quality degrades. A4 therefore keeps golden regression tests, sampled online evaluation, human labels and calibrated judge scores conceptually separate from tracing.

## Current structure

```text
app/
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
├── test_production_observability.py
├── test_agent_security.py
├── test_tool_runtime.py
├── test_mcp_primitives.py
└── ...
```

## Existing ownership boundaries remain intact

- FastAPI owns HTTP/auth/contracts, not long Agent execution.
- RunStore/Queue/Worker own product execution control, not LangGraph checkpoint meaning.
- LangGraph owns graph state/interrupt/resume, not tenant authorization.
- MCP standardizes capability interoperability, not capability permission.
- Tool Runtime owns execution mechanics; a stronger sandbox owns hostile-code containment.
- Security policy owns authority decisions outside the model; trust labels do not sanitize content.
- Observability records execution signals; it does not define quality truth or authorization policy.
- Artifact files and sensitive model/tool payloads stay outside telemetry/context unless explicitly needed and safely handled.

## Next step

**A5 — Distributed / Long-running Agent Runtime.** Turn the existing durable concepts into a real multi-worker topology: at-least-once delivery, leases/heartbeats, stale-worker rejection, retry/backpressure/rate limits, checkpoint recovery, graceful drain and external side-effect idempotency.
