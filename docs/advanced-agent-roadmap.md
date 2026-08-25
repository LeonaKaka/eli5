# Advanced Agent Engineering Roadmap

Scope: six high-density chapters after the core Python → LLM → RAG → Agent → LangGraph → FastAPI line. Advanced chapters are system-oriented, not framework-documentation walkthroughs. Docker, Postgres, Redis, browser runtimes and observability stacks appear only when the engineering problem requires them.

Current progress: **A5 / A6 live**, Research Assistant **v6.6**.

## A1 — MCP / External Capability Ecosystem ✅
Use the existing two MCP pages as one advanced chapter: Host/Client/Server boundaries, Tools vs Resources vs Prompts, control ownership, a real Python SDK v2 `MCPServer`, and a real Client that discovers/calls/reads/renders capabilities. Stop at the architectural boundary: MCP standardizes capability interoperability; the Host still owns authorization, approval, state and side-effect safety. Transport minutiae and protocol-field archaeology are lookup material, not a standalone course.

## A2 — Browser / Shell / Python / Filesystem Runtime ✅
Make an Agent do real work rather than merely emit tool-call JSON. Build a run-scoped workspace, browser adapter, constrained shell runner, separate Python interpreter process and artifact registry. Execute one complete flow: browser → saved source → generated Python → artifact. Learn the difference between application guardrails (cwd, path checks, allowlists, sanitized env, timeout, output bounds) and a genuine security sandbox. Keep real-browser support optional and tests deterministic/offline.

## A3 — Agent Security / Prompt Injection ✅
Attack the A2 runtime with indirect prompt injection from browser/RAG/file content. Separate content trust from application authority: external data is labeled `external_untrusted`, while capabilities come only from authenticated `RunAuthority`. Split fetch from send, keep raw secrets outside model-readable capabilities, enforce egress hosts, require exact-action approval for tainted high-risk execution, and treat injection detection as telemetry rather than the authorization gate. Preserve the distinction between capability policy and real OS/container/VM sandboxing.

## A4 — Production Eval / Observability ✅
Start from the operational failure “success fell from 92% to 78%.” Model one Run as layered spans across agent/model/retrieval/tool/runtime/retry/handoff, then aggregate batches into success/latency/cost/token metrics, per-layer Run failure rates and normalized failure clusters. Compare a baseline with current traffic to identify the layer that regressed rather than guessing from final answers. Keep operational telemetry separate from quality eval: all spans may be green while evidence/answer quality falls. Use golden regression before release plus sampled online eval after rollout, and treat raw prompts/completions/tool payloads as opt-in sensitive telemetry rather than default traces.

## A5 — Distributed / Long-running Agent Runtime ✅
Turn the earlier queue/checkpoint/revision ideas into a real multi-worker ownership model. Queue delivery is explicitly at-least-once; `claim()` creates a time-bounded lease and monotonically increasing fencing token. Heartbeats extend a live lease, a watchdog reaps expired owners and requeues from the latest checkpoint, and stale workers cannot complete or mutate shared state after takeover. Add per-tenant/global admission control, graceful worker drain, and a teaching downstream ledger that combines fencing with idempotency-key replay. Keep the important caveat: external APIs that do not support fencing still need replay-safe contracts or reconciliation rather than blind retries.

## A6 — Agent System Design Capstone
No new framework. Design a Deep Research Agent for roughly 1000 concurrent users and tasks lasting up to hours, with browser/Python/files, approvals, tenant isolation, restart recovery and cost control. Defend every ownership boundary: API vs RunStore vs Queue vs Worker vs LangGraph vs sandbox vs MCP vs event stream vs observability. Finish with failure drills and interview-style architecture review.

## Project evolution
- v6.1–v6.2 — A1 MCP capability interoperability ✅
- v6.3 — A2 real-world tool runtime / workspace / artifacts ✅
- v6.4 — A3 security and untrusted-content boundaries ✅
- v6.5 — A4 production eval / observability ✅
- v6.6 — A5 distributed long-running runtime ✅
- v7.0 — A6 final system-design capstone

## Teaching rule
Advanced material earns a chapter only when it changes engineering judgment. Details that can be looked up in framework documentation stay inside the relevant chapter rather than becoming their own lesson. Every chapter must still include a concrete failure, a runnable project increment and a system-level decision boundary.
