# Research Assistant v4.0

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

Python closed at **Research Agent Lite v1.0**. LLM Application Engineering upgraded the same codebase to **Research Assistant v2.0**. RAG closed at **Research Assistant v3.0**. Agent Engineering now closes at **Research Assistant v4.0**.

Current project level: **v4.0**.

## Agent increments

- **v3.1** — `DecisionKind`, `AgentDecision`, `AgentObservation`, `AgentContext`, `AgentTraceEvent`, `AgentRunResult`, `DecisionMaker`, `AgentLoop`
- **v3.2** — `RunStatus`, `StopReason`, `RunBudget`, `AgentControlState`, `LoopGuard`
- **v3.3** — `PlanStepStatus`, `PlanStep`, `Plan`, `ProgressSignal`, `ReplanDecision`, `ReplanPolicy`, `revised_plan`
- **v3.4** — `MemoryKind`, `MemoryScope`, `MemoryWriteRequest`, `MemoryWritePolicy`, `MemoryStore`
- **v3.5** — `ActionNode`, `ActionGraph`, `ActionResult`, `DependencyPolicy`, `ToolOrchestrator`
- **v3.6** — `ApprovalAction`, `ApprovalRequest`, `ApprovalPolicy`, `ApprovalManager`
- **v3.7** — `DurableAction`, `DurableCheckpoint`, `InMemoryCheckpointStore`, `RecoveryDecision`, `DurableActionRunner`
- **v3.8** — `AgentSpec`, `AgentDirectory`, `SupervisorRouter`, `HandoffContract`, `HandoffGuard`, `HandoffCoordinator`
- **v3.9** — `TrajectoryStepKind`, `TrajectoryStep`, `TrajectoryCase`, `TrajectoryPolicy`, `TrajectoryEvalReport`, `TrajectoryEvaluator`; final task success is separated from tool-choice, unnecessary steps, loop efficiency, handoff/recovery correctness and critical violations
- **v4.0** — `RunRecord`, `RunJob`, `InMemoryRunStore`, `InMemoryRunQueue`, `ProductionControlPlane`; explicit `QUEUED / RUNNING / WAITING_APPROVAL / CANCELLING / CANCELLED` states, tenant-scoped runs, optimistic revisions, duplicate-job rejection, stale-worker protection, abandoned-run requeue, two-phase running cancellation and approval-driven resume

The project remains offline-first. Its in-memory stores, queues, checkpoint store, handoff coordinator and trajectory labels are deterministic teaching implementations. They validate semantics and failure boundaries; they do not pretend to be a distributed database, durable broker, observability backend or production multi-agent runtime.

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
├── agent_loop.py         # v3.1 observe / decide / act / update loop
├── agent_control.py      # run statuses, budgets, stop reasons, queue/cancel states
├── planning.py           # v3.3 explicit plan graph + replan trigger policy
├── memory.py             # v3.4 memory types, write gate, scope, invalidation
├── orchestration.py      # v3.5 dependency waves, output bindings, partial joins
├── approval.py           # v3.6 interrupt / approval / exact-call resume
├── durable.py            # v3.7 checkpoint stages, replay safety, recovery decisions
├── multi_agent.py        # v3.8 typed handoff, ownership, routing, cycle guard
├── trajectory_eval.py    # v3.9 process-level Agent metrics and trace-integrity gate
├── production.py         # v4.0 tenant RunStore, Queue, worker revisions, cancel/requeue/resume
├── tools.py              # ToolRegistry / ToolExecutor permission boundary
├── rag_eval.py           # v3.0 RAG failure taxonomy
├── evals.py              # reusable regression gate
└── ...

tests/
├── test_agent_loop_control.py
├── test_planning_memory.py
├── test_orchestration_approval.py
├── test_durable_multi_agent.py
├── test_trajectory_production.py
└── ...
```

## Why final-answer success is not enough

`TrajectoryEvaluator` treats task success as one dimension. A run can still fail the process-health gate because it selected the wrong tool, added unnecessary steps, delegated to the wrong owner, made an unsafe recovery decision, or crossed a critical approval/policy boundary. Trace indexes must be unique/increasing, a successful run must end in a `FINAL` event, and critical violations are counted across the whole trajectory including the final event. Labels such as `correct` and `necessary` must come from deterministic rules, golden cases, human review, or a separately evaluated judge; the evaluator does not pretend to infer them magically.

## Why the production baseline uses revisions

Real queues can redeliver work, and workers can disappear after claiming work. `ProductionControlPlane` therefore records a run revision in each job. The first worker claim moves the run to a newer revision; a duplicate delivery carrying the old revision is rejected as stale. The revision returned by claim also acts as an optimistic worker token: later worker-side transitions such as `finish()` and `pause_for_approval()` must present the revision they actually claimed. If a watchdog has already requeued an abandoned run and a newer worker has claimed it, the old worker cannot wake up and overwrite the newer state.

`requeue_abandoned()` intentionally assumes lease/heartbeat expiry was detected by external infrastructure. It advances the run revision, preserves the checkpoint reference, returns the run to `QUEUED`, and emits a new `RESUME` job.

## Cancellation semantics

A queued or approval-waiting run can become `CANCELLED` immediately because no worker should be actively advancing it. A `RUNNING` run instead becomes `CANCELLING` with `cancel_requested=True`; this blocks further state transitions until the worker reaches a safe boundary and calls `acknowledge_cancel()`. Cancellation still does not roll back an external side effect that is already `IN_FLIGHT`; replay/reconciliation/compensation remain the durable-action layer's responsibility.

## Durable execution boundary

Durable execution still does **not** claim universal exactly-once semantics. A process can crash after an external side effect but before a committed checkpoint. `IN_FLIGHT` and retryable timeouts therefore remain subject to replay-safety contracts; non-idempotent ambiguous actions require reconciliation.

## Next track

LangChain / LangGraph. The next capability line will map the concepts already built here—state, nodes, conditional edges, checkpointers, interrupts, resumes and handoffs—onto a mainstream orchestration framework instead of relearning Agent engineering from scratch.
