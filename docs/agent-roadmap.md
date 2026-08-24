# Agent Engineering Roadmap — COMPLETE

Scope: evolve Research Assistant v3.0 from a deterministic LLM/RAG application into an autonomous-but-bounded agent whose decisions, tool actions, state transitions, approvals, failures, recovery, handoffs and stopping behavior are explicit and evaluable.

Status: **10/10 complete**. Research Assistant closes this track at **v4.0**.

## 01 — Agent Loop / Autonomy Boundary ✅
Tool calling vs an agent, observe → decide → act → observe/update → stop/continue, decision policy, observations, final answers, loop trace, why one tool call is not yet an agent.

## 02 — State Machine / Stop Conditions / Budgets ✅
Run state, explicit status transitions, max steps, tool-call budget, failure budget, repeated-action detection, no-progress concepts, stop reasons, infinite-loop failure modes and hard safety boundaries.

## 03 — Planning / Replanning ✅
Task decomposition, plan objects, dependencies, milestones, replanning triggers, plan drift, stale plans, dependency ordering, cycle validation and plan revision history.

## 04 — Memory Architecture / Write Policy ✅
Working, episodic, semantic and user memory; write gates, scope, verification, contamination, invalidation, bilingual retrieval baseline and privacy/sensitivity boundaries.

## 05 — Multi-step Tool Orchestration ✅
Action dependencies, sequential vs parallel tools, fan-out/fan-in, result joins, bounded concurrency, output binding, partial failure and action-level observability.

## 06 — Human-in-the-loop / Guardrails / Approval ✅
Read-only vs side-effect vs destructive actions, interrupt/approval checkpoints, least privilege, prompt-injection trust boundaries, exact-call fingerprint binding and single-use resume.

## 07 — Recovery / Durable Execution ✅
Retries vs replay vs resume, checkpoints, replay safety, idempotency contracts, ambiguous IN_FLIGHT state, compensation, crash recovery and reconciliation.

## 08 — Multi-Agent / Handoffs / Supervisor ✅
When one agent is enough, specialist handoffs, supervisor routing, capability gates, explicit ownership, minimal context contracts, shared-state limits and circular delegation protection.

## 09 — Agent Observability / Trajectory Eval ✅
Step traces, task success vs process health, tool-selection accuracy, unnecessary-step rate, loop efficiency, handoff/recovery correctness, critical policy violations, failure taxonomy and Agent regression gates.

## 10 — Production Agent Architecture ✅
Run-oriented APIs, persistent run state, queue/worker separation, optimistic revisions, stale-job rejection, cancellation, approval-driven resume, tenancy/authorization boundaries, production traces and Research Assistant v4.0.

## Project evolution

- v3.1 agent loop + explicit decision/observation trace
- v3.2 loop guard + run budgets + stop reasons
- v3.3 plan / replan boundary
- v3.4 memory policy
- v3.5 multi-step tool orchestration
- v3.6 approvals / guardrails / interrupts
- v3.7 checkpoints / recovery / durable runs
- v3.8 multi-agent handoff contracts
- v3.9 trajectory eval + observability
- v4.0 production run/queue/worker control-plane contract

## Next capability track

LangChain / LangGraph. Framework-specific orchestration was deliberately deferred until the underlying state-machine, checkpoint, interrupt, ownership and recovery problems were understood. The next track should map these concepts onto `StateGraph`, nodes, conditional edges, checkpointers, interrupts and durable resume instead of teaching framework APIs in isolation.
