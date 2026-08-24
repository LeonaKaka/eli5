# Research Assistant v3.8

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

Python closed at **Research Agent Lite v1.0**. LLM Application Engineering upgraded the same codebase to **Research Assistant v2.0**. RAG closed at **Research Assistant v3.0**. The Agent track now evolves the same project toward v4.0.

Current project level: **v3.8**.

## Agent increments

- **v3.1** — `DecisionKind`, `AgentDecision`, `AgentObservation`, `AgentContext`, `AgentTraceEvent`, `AgentRunResult`, `DecisionMaker`, `AgentLoop`; tool results become observations that feed the next decision
- **v3.2** — `RunStatus`, `StopReason`, `RunBudget`, `AgentControlState`, `LoopGuard`; max steps, tool-call budget, failure budget and repeated-action limits stay application-side
- **v3.3** — `PlanStepStatus`, `PlanStep`, `Plan`, `ProgressSignal`, `ReplanDecision`, `ReplanPolicy`, `revised_plan`; dependencies, progress, stale-plan triggers and revision history become explicit
- **v3.4** — `MemoryKind`, `MemoryScope`, `MemoryWriteRequest`, `MemoryWritePolicy`, `MemoryStore`; long-term writes are gated by reuse value, confidence, verification, scope and sensitivity
- **v3.5** — `ActionNode`, `ActionGraph`, `ActionResult`, `DependencyPolicy`, `ToolOrchestrator`; ready nodes execute in dependency waves, outputs can bind into downstream arguments, bounded concurrency prevents unbounded fan-out, and `ALL_DONE` joins can preserve partial results
- **v3.6** — `ApprovalAction`, `ApprovalRequest`, `ApprovalPolicy`, `ApprovalManager`; read-only actions may auto-execute, side effects interrupt into `WAITING_APPROVAL`, destructive actions are denied by default, and resume executes the exact stored ToolCall once
- **v3.7** — `DurableAction`, `DurableCheckpoint`, `InMemoryCheckpointStore`, `RecoveryDecision`, `DurableActionRunner`; recovery distinguishes prepared, in-flight, committed, failed and compensated states instead of replaying every unfinished action
- **v3.8** — `AgentSpec`, `AgentDirectory`, `SupervisorRouter`, `HandoffContract`, `HandoffGuard`, `HandoffCoordinator`; handoffs carry capability requirements, context references, expected output and ownership, while circular delegation is rejected application-side

The project remains offline-first. Durable checkpoints and multi-agent coordination are deterministic control-plane teaching implementations; they do not pretend to be a distributed workflow database, enterprise queue, or production multi-agent runtime.

## Run

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
```

## Agent structure

```text
app/
├── agent_loop.py        # v3.1 observe / decide / act / update loop
├── agent_control.py     # v3.2 run status, budgets, stop reasons, approval-aware states
├── planning.py          # v3.3 explicit plan graph + replan trigger policy
├── memory.py            # v3.4 memory types, write gate, scope, invalidation
├── orchestration.py     # v3.5 dependency waves, output bindings, partial joins
├── approval.py          # v3.6 interrupt / approval / exact-call resume
├── durable.py           # v3.7 checkpoint stages, replay safety, recovery decisions
├── multi_agent.py       # v3.8 typed handoff, ownership, supervisor routing, cycle guard
├── tools.py             # ToolRegistry / ToolExecutor permission boundary
├── rag_eval.py          # v3.0 RAG failure taxonomy reused by Agent eval later
├── evals.py             # reusable regression gate
└── ...

tests/
├── test_agent_loop_control.py
├── test_planning_memory.py
├── test_orchestration_approval.py
├── test_durable_multi_agent.py
└── ...
```

## Why durable execution does not claim exactly-once

A checkpoint can prove that an action was prepared or that a result was committed, but an `IN_FLIGHT` record is intentionally ambiguous: the external system may already have accepted a side effect while the process crashed before persisting the result. `ReplaySafety` therefore distinguishes safe replay, genuine external idempotency and non-idempotent actions. Non-idempotent ambiguous actions require reconciliation instead of blind replay.

## Why multi-agent handoffs are typed

A handoff is a change of task ownership, not a free-form chat message. `HandoffContract` carries the target capability requirement, objective, minimal context references, expected output and return owner. `SupervisorRouter` prefers a least-privileged capable specialist, while `HandoffGuard` rejects capability mismatch, non-owner delegation, delegation-budget exhaustion and circular delegation graphs.

## Next step

Agent 09–10 finish the track with trajectory-level observability/evaluation and a production architecture that combines persistent runs, queues/workers, cancellation, budgets, approvals, recovery, handoffs and regression gates into Research Assistant v4.0.
