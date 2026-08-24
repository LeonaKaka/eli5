# Research Assistant v3.2

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

Python closed at **Research Agent Lite v1.0**. LLM Application Engineering upgraded the same codebase to **Research Assistant v2.0**. RAG closed at **Research Assistant v3.0**. The Agent track now evolves the same project toward v4.0.

Current project level: **v3.2**.

## RAG foundation already inside

The v3.0 baseline already contains structured document ingestion, chunking, embedding/index boundaries, BM25 + hybrid retrieval, reranking, query planning, evidence packing/citation provenance, retrieval metrics and end-to-end RAG failure diagnosis.

## Agent increments

- **v3.1** — `DecisionKind`, `AgentDecision`, `AgentObservation`, `AgentContext`, `AgentTraceEvent`, `AgentRunResult`, `DecisionMaker`, `AgentLoop`; tool results become observations that feed the next decision instead of ending a fixed workflow
- **v3.2** — `RunStatus`, `StopReason`, `RunBudget`, `AgentControlState`, `LoopGuard`; max steps, tool-call budget, failure budget and repeated-action limits are enforced outside the model

`ScriptedDecisionMaker` remains a deterministic teaching adapter. It exists so the control loop can be tested offline; it is not presented as a production planner or reasoning model.

## Run

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

python -m app.main "RAG evaluation"
pytest -q
```

## Agent structure

```text
app/
├── agent_loop.py        # v3.1 observe / decide / act / update loop
├── agent_control.py     # v3.2 run status, budgets, stop reasons, loop guard
├── tools.py             # ToolRegistry / ToolExecutor permission boundary
├── rag_eval.py          # v3.0 RAG failure taxonomy reused by Agent eval later
├── evals.py             # reusable regression gate
└── ...

tests/
├── test_agent_loop_control.py
└── ...
```

## Why Tool Calling and Agent Loop stay separate

A model proposing a `ToolCall` is not itself the control loop. `AgentLoop` decides when to ask for another decision after an observation, while `ToolExecutor` still owns validation, permission checks and real execution. This keeps model autonomy bounded by application-side controls.

## Why LoopGuard is application-side

A prompt can ask the model not to repeat itself, but it cannot be the only hard boundary. `LoopGuard` can independently terminate a run when step/tool/failure/repetition budgets are exhausted, even if the model keeps proposing another action.

## Next step

Agent 03–04 will add explicit planning/replanning and memory write/read policy. Planning will build on the stop/progress signals introduced here instead of assuming every long task should blindly follow one initial plan.
