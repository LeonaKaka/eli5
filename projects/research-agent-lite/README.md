# Research Assistant v3.6

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

Python closed at **Research Agent Lite v1.0**. LLM Application Engineering upgraded the same codebase to **Research Assistant v2.0**. RAG closed at **Research Assistant v3.0**. The Agent track now evolves the same project toward v4.0.

Current project level: **v3.6**.

## Agent increments

- **v3.1** — `DecisionKind`, `AgentDecision`, `AgentObservation`, `AgentContext`, `AgentTraceEvent`, `AgentRunResult`, `DecisionMaker`, `AgentLoop`; tool results become observations that feed the next decision
- **v3.2** — `RunStatus`, `StopReason`, `RunBudget`, `AgentControlState`, `LoopGuard`; max steps, tool-call budget, failure budget and repeated-action limits stay application-side
- **v3.3** — `PlanStepStatus`, `PlanStep`, `Plan`, `ProgressSignal`, `ReplanDecision`, `ReplanPolicy`, `revised_plan`; dependencies, progress, stale-plan triggers and revision history become explicit
- **v3.4** — `MemoryKind`, `MemoryScope`, `MemoryWriteRequest`, `MemoryWritePolicy`, `MemoryStore`; long-term writes are gated by reuse value, confidence, verification, scope and sensitivity
- **v3.5** — `ActionNode`, `ActionGraph`, `ActionResult`, `DependencyPolicy`, `ToolOrchestrator`; ready nodes execute in dependency waves, outputs can bind into downstream arguments, bounded concurrency prevents unbounded fan-out, and `ALL_DONE` joins can preserve partial results
- **v3.6** — `ApprovalAction`, `ApprovalRequest`, `ApprovalPolicy`, `ApprovalManager`; read-only actions may auto-execute, side effects interrupt into `WAITING_APPROVAL`, destructive actions are denied by default, and resume executes the exact stored ToolCall once

The project remains offline-first. The orchestration graph and approval manager are deterministic control-plane teaching implementations; they do not pretend to be a distributed workflow engine or enterprise authorization platform.

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
├── tools.py             # ToolRegistry / ToolExecutor permission boundary
├── rag_eval.py          # v3.0 RAG failure taxonomy reused by Agent eval later
├── evals.py             # reusable regression gate
└── ...

tests/
├── test_agent_loop_control.py
├── test_planning_memory.py
├── test_orchestration_approval.py
└── ...
```

## Why orchestration is separate from planning

A `Plan` says which subgoals exist and how they depend on each other. `ToolOrchestrator` executes a concrete action graph: it finds ready nodes, runs independent nodes concurrently, binds upstream outputs into downstream tool arguments and normalizes partial failure. `ToolExecutor` still owns one tool call's validation and execution boundary.

## Why approval binds to an exact ToolCall

Approval must cover the action that is actually executed. `ApprovalManager` stores a canonical fingerprint and the proposed `ToolCall`, enters `WAITING_APPROVAL`, then resumes that stored call after an explicit reviewer decision. It does not ask the model to regenerate a new action after approval, and a resolved approval request cannot be executed twice.

## Next step

Agent 07–08 add durable execution and multi-agent handoffs. Durable execution will persist checkpoints around actions and approval interrupts so a crash can resume safely without repeating side effects; multi-agent work will then add typed handoff contracts and explicit ownership rather than shared free-form chat.
