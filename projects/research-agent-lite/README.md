# Research Assistant v4.4

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

Python closed at **Research Agent Lite v1.0**. LLM Application Engineering upgraded the same codebase to **Research Assistant v2.0**. RAG closed at **Research Assistant v3.0**. Agent Engineering closed at **Research Assistant v4.0**. The LangChain / LangGraph track now migrates the same project toward v5.0.

Current project level: **v4.4**.

## Framework track increments

- **v4.1** — `BridgeState`, `build_bridge_graph()` and the first real compiled LangGraph; deterministic/model-free execution proves the State → Node update → Edge → runnable contract
- **v4.2** — `ResearchGraphState`, append reducers for `events/evidence`, fixed and conditional edges, deterministic routing, and branch rejoin into synthesis
- **v4.3** — `@tool search_papers`, `ToolNode`, `tools_condition`, real `AIMessage.tool_calls` and correlated `ToolMessage.tool_call_id`; the model node is deterministic only so the real tool protocol can be tested without a provider key
- **v4.4** — `Command(update=..., goto=...)` for atomic update+routing decisions and `Send` for dynamic fan-out/map-reduce with reducer-based fan-in

The project depends on `langchain>=1.3,<2` and `langgraph>=1.2,<2`. Lessons 01–04 do not call any external model provider and therefore do not require an API key.

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
├── langgraph_basics.py         # v4.1-v4.2 compiled graph, typed state, reducers, routing
├── langgraph_tools.py          # v4.3 @tool, ToolNode, tools_condition, ToolMessage loop
├── langgraph_control_flow.py   # v4.4 Command + Send / dynamic fan-out and fan-in
├── agent_loop.py               # manual v3.1 observe / decide / act / update loop
├── agent_control.py            # run statuses, budgets, stop reasons, queue/cancel states
├── planning.py                 # explicit plan graph + replan trigger policy
├── memory.py                   # memory types, write gate, scope, invalidation
├── orchestration.py            # dependency waves, output bindings, partial joins
├── approval.py                 # application approval policy remains independent
├── durable.py                  # replay-safety and reconciliation contracts
├── multi_agent.py              # typed handoff, ownership, routing, cycle guard
├── trajectory_eval.py          # process-level Agent metrics and trace integrity
├── production.py               # tenant RunStore, Queue, worker revisions, cancel/requeue/resume
└── ...

tests/
├── test_langgraph_basics.py
├── test_langgraph_tools_control.py
├── test_agent_loop_control.py
├── test_planning_memory.py
├── test_orchestration_approval.py
├── test_durable_multi_agent.py
├── test_trajectory_production.py
└── ...
```

## ToolNode lesson boundary

`ToolNode` is an execution primitive, not a complete authorization layer. A real model may emit one or more tool calls; `ToolNode` executes registered calls and returns `ToolMessage` results that retain the originating `tool_call_id`. The course's deterministic model node emits a real `AIMessage.tool_calls` payload only to keep tests provider-free. Replacing that node with a chat model does not change the graph's ToolNode/ToolMessage contract.

`tools_condition` models the standard ReAct-style branch: last AI message has tool calls → route to `tools`; no tool calls → end. More complex approval, planning and business stop conditions still require explicit graph/application logic.

## Command and Send lesson boundary

Use a conditional edge when routing can be cleanly separated from the node's update. Use `Command` when one decision naturally needs to update state and choose the next hop together. Use `Send` when the number of downstream tasks and their individual input states are only known at runtime.

The v4.4 map-reduce graph follows the framework's dynamic fan-out pattern: each query becomes `Send("retrieve_one", {"query": ...})`, worker updates append into a reducer-backed `evidence` field, and a downstream summarize node consumes the merged state. This does not imply unlimited concurrency is safe; provider rate limits, cost budgets and infrastructure concurrency remain separate controls.

## What remains application-side

The framework migration does not erase tenant authorization, Tool permissions, side-effect approval, replay safety, cancellation, memory write policy or regression gates. Later lessons map persistence/interrupt/memory/subgraph concerns onto LangGraph primitives, but business and infrastructure contracts remain explicit.

## Next step

LangChain / LangGraph 05–06 add checkpointers, threads, state history and durable `interrupt()` / `Command(resume=...)` flows. That is where the framework starts replacing a larger part of the hand-built persistence/resume boilerplate from Agent 06–07.
