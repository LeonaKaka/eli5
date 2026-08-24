# Agent Engineering Roadmap

Scope: evolve Research Assistant v3.0 from a deterministic LLM/RAG application into an autonomous-but-bounded agent whose decisions, tool actions, state transitions, approvals, failures and stopping behavior are explicit and evaluable.

## 01 — Agent Loop / Autonomy Boundary
Tool calling vs an agent, observe → decide → act → observe/update → stop/continue, decision policy, observations, final answers, loop trace, why one tool call is not yet an agent.

## 02 — State Machine / Stop Conditions / Budgets
Run state, explicit status transitions, max steps, tool-call budget, failure budget, repeated-action detection, no-progress detection, stop reasons, infinite-loop failure modes and hard safety boundaries.

## 03 — Planning / Replanning
Task decomposition, plan objects, milestones, plan execution vs immediate acting, replanning triggers, plan drift, stale plans, dependency ordering and plan-quality evaluation.

## 04 — Memory Architecture / Write Policy
Working memory, episodic memory, semantic/user memory, memory retrieval, what deserves persistence, memory write gates, summarization, stale/incorrect memory, contamination and privacy boundaries.

## 05 — Multi-step Tool Orchestration
Action dependencies, sequential vs parallel tools, fan-out/fan-in, result joins, tool-result normalization, partial failure, dependency graphs and action-level observability.

## 06 — Human-in-the-loop / Guardrails / Approval
Read-only vs side-effect actions, interrupt/approval checkpoints, least privilege, policy checks, prompt injection boundaries, tool-output trust, destructive actions and human override.

## 07 — Recovery / Durable Execution
Retries vs resuming, checkpoints, replay safety, idempotency, deduplication, compensation, partial completion, crash recovery and deterministic continuation.

## 08 — Multi-Agent / Handoffs / Supervisor
When one agent is enough, specialist handoffs, supervisor patterns, shared vs isolated state, message contracts, coordination cost, circular delegation and multi-agent anti-patterns.

## 09 — Agent Observability / Trajectory Eval
Step traces, decision quality, tool-selection accuracy, unnecessary-step rate, loop efficiency, recovery quality, trajectory-level golden cases, failure taxonomy and agent regression gates.

## 10 — Production Agent Architecture
Long-running jobs, queues/workers, concurrency, persistence, per-run budgets, cancellation, tenancy/permissions, production traces, deployment boundaries and Research Assistant v4.0.

## Project evolution
Continue `projects/research-agent-lite/` from Research Assistant v3.0:
- v3.1 agent loop + explicit decision/observation trace
- v3.2 loop guard + run budgets + stop reasons
- v3.3 plan / replan boundary
- v3.4 memory policy
- v3.5 multi-step tool orchestration
- v3.6 approvals / guardrails / interrupts
- v3.7 checkpoints / recovery / durable runs
- v3.8 multi-agent handoff contracts
- v3.9 trajectory eval + observability
- v4.0 production agent architecture

Framework-specific orchestration (especially LangGraph) comes in the next capability track. The goal here is to understand the underlying state-machine and control problems before learning a framework abstraction.