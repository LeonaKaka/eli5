# Research Assistant v4.2

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

Python closed at **Research Agent Lite v1.0**. LLM Application Engineering upgraded the same codebase to **Research Assistant v2.0**. RAG closed at **Research Assistant v3.0**. Agent Engineering closed at **Research Assistant v4.0**. The LangChain / LangGraph track now migrates the same project toward v5.0.

Current project level: **v4.2**.

## Framework track increments

- **v4.1** — `BridgeState`, `build_bridge_graph()` and the first real compiled LangGraph; the graph is deterministic/model-free and proves the State → Node update → Edge → runnable execution contract
- **v4.2** — `ResearchGraphState`, append reducers for `events/evidence`, fixed and conditional edges, deterministic routing, and branch rejoin into synthesis

The project now depends on current framework major lines used by the course: `langchain>=1.3,<2` and `langgraph>=1.2,<2`. The first two lessons do not call any external model provider and therefore do not require an API key.

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
├── langgraph_basics.py    # v4.1-v4.2 compiled graph, typed state, reducers, routing
├── agent_loop.py          # v3.1 manual observe / decide / act / update loop
├── agent_control.py       # run statuses, budgets, stop reasons, queue/cancel states
├── planning.py            # explicit plan graph + replan trigger policy
├── memory.py              # memory types, write gate, scope, invalidation
├── orchestration.py       # dependency waves, output bindings, partial joins
├── approval.py            # interrupt-independent application approval policy
├── durable.py             # replay-safety and reconciliation contracts
├── multi_agent.py         # typed handoff, ownership, routing, cycle guard
├── trajectory_eval.py     # process-level Agent metrics and trace integrity
├── production.py          # tenant RunStore, Queue, worker revisions, cancel/requeue/resume
└── ...

tests/
├── test_langgraph_basics.py
├── test_agent_loop_control.py
├── test_planning_memory.py
├── test_orchestration_approval.py
├── test_durable_multi_agent.py
├── test_trajectory_production.py
└── ...
```

## Why migration is incremental

`StateGraph` replaces orchestration boilerplate; it does not erase business semantics. The existing RAG pipeline, Tool contracts, authorization, approval policy, replay-safety logic, tenant isolation and eval boundaries remain valid. Later lessons will map some of those concerns to `ToolNode`, checkpointers, interrupts, Store, subgraphs and middleware, but each mapping must preserve the original safety/control contract.

## StateGraph lesson boundary

The v4.2 graph deliberately uses a custom typed state rather than stuffing everything into messages. Nodes return partial state updates. `events` and `evidence` use append reducers while scalar fields such as `answer` use the default overwrite behavior. Conditional edges make routing visible instead of hiding downstream calls inside a node.

## Next step

LangChain / LangGraph 03–04 add real LangChain `@tool` definitions, `ToolNode`, and the model↔tools loop, then move into richer control flow with conditional edges, `Command` and `Send`.
