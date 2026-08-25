# Research Assistant v6.4

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

Python closed at **v1.0**, LLM Application Engineering at **v2.0**, RAG at **v3.0**, Agent Engineering at **v4.0**, LangChain / LangGraph at **v5.0**, FastAPI closed the backend architecture at **v6.0**, and the compressed Advanced Agent Engineering line now extends the same system.

## Advanced increments

- **v6.1–v6.2 / A1 MCP** — capability interoperability: Host/Client/Server, Tool/Resource/Prompt control ownership, real Python SDK v2 `MCPServer` + `Client` discovery/call/read/get. A1 stops here; MCP protocol minutiae are lookup material rather than ten more lessons.
- **v6.3 / A2 Tool Runtime** — run-scoped workspace, browser adapter, constrained shell runner, separate Python interpreter process and artifact registry. The teaching flow is browser → saved source → generated Python → artifact.
- **v6.4 / A3 Agent Security** — external-content trust labels, authenticated RunAuthority, separate read/send network capabilities, secret isolation, exact-action approval and host-side decisions that prevent prompt text from silently granting privilege.

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

The tests do not require a network or browser binary; they use `FixtureBrowser` while exercising the same `BrowserAdapter` boundary.

## A2 runtime architecture

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

## A3 trust and authority model

Prompt injection is treated as an authority-confusion problem rather than a string-filtering problem.

```text
Browser / RAG / file / tool output
        │
        ▼
ContextChunk
trust = external_untrusted
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

`ContentTrust` and `RunAuthority` are deliberately separate. Untrusted text can influence model reasoning, but it cannot expand product permissions.

Current capability examples:

```text
READ_WORKSPACE
WRITE_WORKSPACE
RUN_PYTHON
RUN_SHELL
NETWORK_FETCH
NETWORK_SEND
READ_SECRET
```

Important rules:

- `READ_SECRET` is always denied as a model-readable capability. Raw credentials stay in the Host/connector and should be injected only into the downstream trusted integration that needs them.
- `NETWORK_FETCH` and `NETWORK_SEND` are separate capabilities. Being able to read a paper does not imply permission to upload arbitrary data.
- Network targets must be inside `RunAuthority.allowed_egress_hosts`.
- Sensitive actions proposed while external untrusted content is in context can require human approval.
- `ApprovalGrant` is bound to the exact `ToolIntent.fingerprint()`. Approving one Python action cannot be replayed as approval for a later network send or different command.
- A prompt-injection detector is only a telemetry/risk signal. `injection_signal()` intentionally has false negatives; security correctness must not depend on detector recall.

## A3 adversarial regression tests

`tests/test_agent_security.py` covers:

```text
malicious browser text → trust = external_untrusted
raw secret read        → DENY
send to evil host      → DENY by egress scope
tainted Python/Shell   → APPROVAL_REQUIRED
wrong approval token   → DENY
exact approval         → ALLOW
missing run capability → DENY
fetch-only authority   → cannot become NETWORK_SEND
paraphrased injection  → detector can miss it, policy still holds
```

The tests are intentionally provider-free. They test the security boundary even if a future model sometimes resists prompt injection by itself.

## Current structure

```text
app/
├── agent_security.py             # A3 trust / capability / approval policy
├── tool_runtime.py               # A2 browser/filesystem/shell/python/artifacts
├── mcp_contracts.py              # A1 primitive/control ownership policy
├── mcp_research_server.py        # A1 MCPServer + research capabilities
├── fastapi_app.py                # HTTP product API / health / SSE / commands
├── fastapi_service.py            # v6 composition root / deployment audit
├── fastapi_security.py           # Bearer / Principal / permissions
├── fastapi_errors.py             # ProblemDetails / request correlation
├── fastapi_worker.py             # separate Worker adapter
├── langgraph_production.py       # control-plane ↔ LangGraph bridge
└── production.py                 # tenant RunStore / Queue / optimistic revisions

tests/
├── test_agent_security.py
├── test_tool_runtime.py
├── test_mcp_primitives.py
├── test_fastapi_lifecycle_production.py
└── ...
```

## Existing ownership boundaries remain intact

- FastAPI owns HTTP/auth/contracts, not long Agent execution.
- RunStore/Queue/Worker own product execution control, not LangGraph checkpoint meaning.
- LangGraph owns graph state/interrupt/resume, not tenant authorization.
- MCP standardizes capability interoperability, not capability permission.
- Tool Runtime owns execution mechanics; a stronger sandbox owns hostile-code containment.
- Security policy owns authority decisions outside the model; trust labels do not sanitize content.
- Artifact files stay outside model context unless explicitly summarized/read back in.

## Next step

**A4 — Production Eval / Observability.** Start from a real operational failure: Agent success rate falls from 92% to 78%. Connect Run → model/retrieval/tool/retry/runtime events, latency/token/cost metrics, regression sets and failure clustering so the team can identify which layer actually regressed instead of guessing from final answers.
