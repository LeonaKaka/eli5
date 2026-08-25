# Advanced Agent Engineering Roadmap

Scope: six high-density chapters after the core Python → LLM → RAG → Agent → LangGraph → FastAPI line. Advanced chapters are system-oriented, not framework-documentation walkthroughs. Docker, Postgres, Redis, browser runtimes and observability stacks appear only when the engineering problem requires them.

Current progress: **A6 / A6 complete**, Research Assistant **v7.0**.

## A1 — MCP / External Capability Ecosystem ✅
Host/Client/Server boundaries, Tools vs Resources vs Prompts, control ownership, real Python SDK v2 `MCPServer` + `Client`, stopping at the architecture boundary rather than protocol archaeology.

## A2 — Browser / Shell / Python / Filesystem Runtime ✅
Run-scoped workspace, browser adapter, constrained shell runner, separate Python interpreter process and artifact registry. The complete flow is browser → saved source → generated Python → artifact, while explicitly distinguishing application guardrails from a genuine hostile-code sandbox.

## A3 — Agent Security / Prompt Injection ✅
Attack A2 with indirect prompt injection. Keep external data `external_untrusted`; grant capability only through authenticated `RunAuthority`; split fetch/send; isolate secrets; enforce egress scope; bind approval to an immutable exact action plus authorized approver; treat injection detection as telemetry rather than authorization.

## A4 — Production Eval / Observability ✅
Diagnose the incident “success fell from 92% to 78%” with layered Run traces, success/latency/cost/token metrics, per-layer failure rates, normalized failure clusters and baseline-vs-current diagnosis. Keep operational telemetry separate from quality truth: spans may be green while evidence/answer quality regresses.

## A5 — Distributed / Long-running Agent Runtime ✅
Use explicit at-least-once Queue delivery, time-bounded worker leases, heartbeats, monotonic fencing tokens, checkpoint takeover, stale-worker rejection, admission control and graceful drain. Preserve the side-effect caveat: external systems without fencing/idempotency support require reconciliation rather than blind replay.

## A6 — Agent System Design Capstone ✅
No new framework. Design a roughly 1,000-concurrent-user Deep Research Agent with hours-long Runs, Browser/Python/files, approvals, tenant isolation, restart recovery and cost control. The final system is reviewed by ownership rather than vendor names:

```text
Identity                 → Identity/Auth
Product Run truth        → RunStore
Delivery                 → Queue
Execution ownership      → Lease + Fencing
Graph continuation       → LangGraph Checkpointer
Tool authority           → Host Security Policy
Hostile-code isolation   → Sandbox
Durable artifacts        → Object Storage
Client incremental view  → Event Store / SSE
Operational health       → Observability
Quality truth            → Eval
External-effect safety   → Idempotency / Fencing / Reconciliation
```

A6 adds `CapstoneArchitectureReviewer`, which rejects responsibility confusion such as Queue-as-RunStore, checkpoint-as-auth, LLM-as-permission-owner, SSE-as-product-truth or subprocess-as-security-sandbox. Failure drills cover Worker crash/zombie takeover, duplicate delivery, malicious web content, quality regression, SSE disconnect, RunStore outage, ambiguous side effects and overload.

Full final reference: `docs/agent-system-design-capstone.md`.

## Project evolution
- v6.1–v6.2 — A1 MCP capability interoperability ✅
- v6.3 — A2 real-world tool runtime / workspace / artifacts ✅
- v6.4 — A3 security and untrusted-content boundaries ✅
- v6.5 — A4 production eval / observability ✅
- v6.6 — A5 distributed long-running runtime ✅
- **v7.0 — A6 final system-design capstone ✅**

## Course-complete rule

The main Agent-engineering learning line is complete when a design can be defended by **owner + failure mode + recovery invariant**, rather than by naming a framework. Future topics such as Kubernetes, Temporal, Postgres/Redis tuning, a specific cloud provider, new MCP transports, sandbox products or observability backends are implementation choices that should be learned when a real project needs them.

Course completion does not mean the teaching profile's in-memory adapters are production infrastructure. A real deployment must still provide shared durable implementations that satisfy the contracts learned here.
