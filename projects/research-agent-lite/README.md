# Research Assistant v3.4

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

Python closed at **Research Agent Lite v1.0**. LLM Application Engineering upgraded the same codebase to **Research Assistant v2.0**. RAG closed at **Research Assistant v3.0**. The Agent track now evolves the same project toward v4.0.

Current project level: **v3.4**.

## Agent increments

- **v3.1** — `DecisionKind`, `AgentDecision`, `AgentObservation`, `AgentContext`, `AgentTraceEvent`, `AgentRunResult`, `DecisionMaker`, `AgentLoop`; tool results become observations that feed the next decision
- **v3.2** — `RunStatus`, `StopReason`, `RunBudget`, `AgentControlState`, `LoopGuard`; max steps, tool-call budget, failure budget and repeated-action limits stay application-side
- **v3.3** — `PlanStepStatus`, `PlanStep`, `Plan`, `ProgressSignal`, `ReplanDecision`, `ReplanPolicy`, `revised_plan`; dependencies, progress, stale-plan triggers and revision history become explicit
- **v3.4** — `MemoryKind`, `MemoryScope`, `MemoryWriteRequest`, `MemoryWritePolicy`, `MemoryStore`; long-term writes are gated by reuse value, confidence, verification, scope and sensitivity, while invalidated memories remain auditable but stop participating in retrieval

`ScriptedDecisionMaker`, the explicit replan trigger policy and the in-memory MemoryStore remain deterministic teaching components. They validate control boundaries offline rather than pretending to be production reasoning, vector memory or personalization infrastructure.

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
├── agent_control.py     # v3.2 run status, budgets, stop reasons, loop guard
├── planning.py          # v3.3 explicit plan graph + replan trigger policy
├── memory.py            # v3.4 memory types, write gate, scope, invalidation
├── tools.py             # ToolRegistry / ToolExecutor permission boundary
├── rag_eval.py          # v3.0 RAG failure taxonomy reused by Agent eval later
├── evals.py             # reusable regression gate
└── ...

tests/
├── test_agent_loop_control.py
├── test_planning_memory.py
└── ...
```

## Why planning is explicit

A long-running agent needs more than a hidden natural-language TODO. `Plan` carries stable step ids, dependencies, status and revision. `ReplanPolicy` decides when the current plan is stale enough to revisit, while replacement-plan generation remains a separate concern. This makes plan thrashing and no-progress behavior observable.

## Why memory writes are gated

Every observation is not durable knowledge. The v3.4 store rejects working-memory events, sensitive content, unconfirmed user memory, unverified semantic memory, low-confidence facts and information without demonstrated cross-run reuse value. Search also respects memory scope and ignores invalidated records.

## Next step

Agent 05–06 add multi-step tool orchestration and human-in-the-loop guardrails. Those lessons will use plan dependencies to decide sequential vs parallel actions, then add explicit approval/interrupt boundaries before side effects.
