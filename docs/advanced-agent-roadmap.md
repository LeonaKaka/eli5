# Advanced Agent Engineering Roadmap

Scope: six high-density chapters after the core Python → LLM → RAG → Agent → LangGraph → FastAPI line. Advanced chapters are system-oriented, not framework-documentation walkthroughs. Docker, Postgres, Redis, browser runtimes and observability stacks appear only when the engineering problem requires them.

Current progress: **A2 / A6 live**, Research Assistant **v6.3**.

## A1 — MCP / External Capability Ecosystem ✅
Use the existing two MCP pages as one advanced chapter: Host/Client/Server boundaries, Tools vs Resources vs Prompts, control ownership, a real Python SDK v2 `MCPServer`, and a real Client that discovers/calls/reads/renders capabilities. Stop at the architectural boundary: MCP standardizes capability interoperability; the Host still owns authorization, approval, state and side-effect safety. Transport minutiae and protocol-field archaeology are lookup material, not a standalone course.

## A2 — Browser / Shell / Python / Filesystem Runtime ✅
Make an Agent do real work rather than merely emit tool-call JSON. Build a run-scoped workspace, browser adapter, constrained shell runner, separate Python interpreter process and artifact registry. Execute one complete flow: browser → saved source → generated Python → artifact. Learn the difference between application guardrails (cwd, path checks, allowlists, sanitized env, timeout, output bounds) and a genuine security sandbox. Keep real-browser support optional and tests deterministic/offline.

## A3 — Agent Security / Prompt Injection
Attack the A2 runtime. Feed indirect prompt injection through browser/RAG/file content; test attempts to read secrets, escape paths, abuse network access, invoke dangerous tools and smuggle instructions through tool outputs. Build trust labels/capability scopes and explicit approval boundaries. The goal is not a perfect universal defense; it is knowing where untrusted data crosses into authority and which controls must exist outside the model.

## A4 — Production Eval / Observability
Start from an operational question: success rate fell from 92% to 78%—why? Connect Run → model/retrieval/tool/retry/handoff spans, latency/token/cost/error metrics and structured trajectory events. Add golden regressions, sampled online eval, calibrated LLM judges, human review and failure clustering. Separate product telemetry, debugging traces, audit records and quality evaluation.

## A5 — Distributed / Long-running Agent Runtime
Scale the existing durable concepts into a real multi-worker topology. Cover at-least-once delivery, worker lease/heartbeat, stale workers, retries, backpressure, rate limits, checkpoint recovery, idempotent external effects and graceful drain. Use Postgres/Redis/Docker only as implementation tools when needed; do not turn them into separate syllabus tracks.

## A6 — Agent System Design Capstone
No new framework. Design a Deep Research Agent for roughly 1000 concurrent users and tasks lasting up to hours, with browser/Python/files, approvals, tenant isolation, restart recovery and cost control. Defend every ownership boundary: API vs RunStore vs Queue vs Worker vs LangGraph vs sandbox vs MCP vs event stream vs observability. Finish with failure drills and interview-style architecture review.

## Project evolution
- v6.1–v6.2 — A1 MCP capability interoperability ✅
- v6.3 — A2 real-world tool runtime / workspace / artifacts ✅
- v6.4 — A3 security and untrusted-content boundaries
- v6.5 — A4 production eval / observability
- v6.6 — A5 distributed long-running runtime
- v7.0 — A6 final system-design capstone

## Teaching rule
Advanced material earns a chapter only when it changes engineering judgment. Details that can be looked up in framework documentation stay inside the relevant chapter rather than becoming their own lesson. Every chapter must still include a concrete failure, a runnable project increment and a system-level decision boundary.