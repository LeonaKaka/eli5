# Research Assistant v4.6

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

Python closed at **Research Agent Lite v1.0**. LLM Application Engineering upgraded the same codebase to **Research Assistant v2.0**. RAG closed at **Research Assistant v3.0**. Agent Engineering closed at **Research Assistant v4.0**. The LangChain / LangGraph track now migrates the same project toward v5.0.

Current project level: **v4.6**.

## Framework track increments

- **v4.1** — `BridgeState`, `build_bridge_graph()` and the first real compiled LangGraph
- **v4.2** — `ResearchGraphState`, reducers, fixed/conditional edges and branch rejoin
- **v4.3** — `@tool search_papers`, `ToolNode`, `tools_condition`, real `AIMessage.tool_calls` and correlated `ToolMessage.tool_call_id`
- **v4.4** — `Command(update=..., goto=...)` and `Send` dynamic fan-out/map-reduce with reducer-based fan-in
- **v4.5** — `PersistenceState`, `InMemorySaver`, `thread_config()`, real thread-scoped checkpoints, `get_state()`, `get_state_history()` and `update_state()`
- **v4.6** — `ApprovalState`, real `interrupt()` + `Command(resume=...)`, safe approval graph and deliberately unsafe pre-interrupt replay demo

The project depends on `langchain>=1.3,<2` and `langgraph>=1.2,<2`. Lessons 01–06 do not call any external model provider and therefore do not require an API key.

## Run

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
```

## Current structure

```text
app/
├── langgraph_basics.py          # v4.1-v4.2 StateGraph, typed state, reducers, routing
├── langgraph_tools.py           # v4.3 @tool, ToolNode, tools_condition, ToolMessage loop
├── langgraph_control_flow.py    # v4.4 Command + Send / dynamic fan-out and fan-in
├── langgraph_persistence.py     # v4.5 checkpointer, thread config, checkpoint history
├── langgraph_interrupts.py      # v4.6 interrupt / resume / replay-safe approval layout
├── agent_loop.py                # manual v3.1 observe / decide / act / update loop
├── agent_control.py             # run statuses, budgets, stop reasons, queue/cancel states
├── planning.py                  # explicit plan graph + replan trigger policy
├── memory.py                    # memory types, write gate, scope, invalidation
├── orchestration.py             # dependency waves, output bindings, partial joins
├── approval.py                  # application approval policy remains independent
├── durable.py                   # replay-safety and reconciliation contracts
├── multi_agent.py               # typed handoff, ownership, routing, cycle guard
├── trajectory_eval.py           # process-level Agent metrics and trace integrity
├── production.py                # tenant RunStore, Queue, worker revisions, cancel/requeue/resume
└── ...

tests/
├── test_langgraph_basics.py
├── test_langgraph_tools_control.py
├── test_langgraph_persistence_interrupts.py
├── test_agent_loop_control.py
├── test_planning_memory.py
├── test_orchestration_approval.py
├── test_durable_multi_agent.py
├── test_trajectory_production.py
└── ...
```

## Persistence boundary

`InMemorySaver` demonstrates the real LangGraph checkpointer contract but is intentionally non-durable across process restarts. A checkpointer stores graph-state snapshots by `thread_id`; `get_state()` returns the latest `StateSnapshot`, and `get_state_history()` exposes historical checkpoints newest-first. `update_state()` creates another checkpoint rather than mutating an old snapshot in place.

Checkpointer state is **not** the same thing as the v4.0 product control plane. Tenant authorization, queue delivery, worker leases/revisions, cancellation and product-level run ownership still belong outside the graph unless deliberately integrated. Cross-thread durable facts belong to a Store, which is covered in lesson 07.

## Interrupt boundary

`interrupt()` requires a checkpointer and a stable `thread_id`. The payload is surfaced to the caller, and resuming with `Command(resume=value)` injects that value back as the return value of `interrupt()`.

The interrupted node restarts from its beginning when resumed. Therefore code before `interrupt()` must be pure, idempotent or otherwise replay-safe. `build_unsafe_pre_interrupt_graph()` intentionally demonstrates a duplicated side effect during pause/resume; `build_approval_graph()` moves the side effect into a downstream node after approval.

Interrupt persistence is not an authorization policy. The application still decides which actions require approval, who can approve them, how an approval is bound to an exact action, and how side effects are reconciled after ambiguous external outcomes.

## Next step

LangChain / LangGraph 07–08 add cross-thread Store-backed long-term memory and subgraph/multi-agent composition. That is where thread-local graph state starts interacting with durable user/workspace memory and specialist graph boundaries.
