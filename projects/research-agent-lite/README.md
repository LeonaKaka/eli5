# Research Assistant v5.0

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

Python closed at **Research Agent Lite v1.0**, LLM Application Engineering at **v2.0**, RAG at **v3.0**, Agent Engineering at **v4.0**, and the LangChain / LangGraph track now closes at **Research Assistant v5.0**.

## Framework increments

- **v4.1** — first real compiled `StateGraph`
- **v4.2** — typed graph state, reducers and conditional routing
- **v4.3** — `@tool`, `ToolNode`, `tools_condition`, correlated `ToolMessage.tool_call_id`
- **v4.4** — `Command(update=..., goto=...)` and `Send` dynamic fan-out/fan-in
- **v4.5** — `InMemorySaver`, `thread_id`, StateSnapshot/history/update-state
- **v4.6** — real `interrupt()` + `Command(resume=...)` and unsafe replay demo
- **v4.7** — `BaseStore`/`InMemoryStore`, Runtime context, namespace design, cross-thread memory + existing `MemoryWritePolicy`
- **v4.8** — shared/private subgraphs and `Command.PARENT` handoff
- **v4.9** — real `AgentMiddleware` hook contract plus LangGraph v2 `updates` / `values` / `custom` streaming
- **v5.0** — `ProductionGraphBridge` connecting LangGraph thread/checkpoint/interrupt semantics to the existing tenant-scoped `ProductionControlPlane`

The project depends on `langchain>=1.3,<2` and `langgraph>=1.2,<2`. The course keeps framework demos provider-free where possible, so the Graph and control-plane examples do not require an external model key.

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
├── langgraph_basics.py          # v4.1-v4.2 StateGraph / typed state / reducers
├── langgraph_tools.py           # v4.3 ToolNode / tools_condition
├── langgraph_control_flow.py    # v4.4 Command / Send
├── langgraph_persistence.py     # v4.5 thread / checkpointer / history
├── langgraph_interrupts.py      # v4.6 interrupt / resume
├── langgraph_store.py           # v4.7 BaseStore / Runtime context / memory policy
├── langgraph_subgraphs.py       # v4.8 shared/private subgraphs / Command.PARENT
├── langgraph_observability.py   # v4.9 AgentMiddleware + v2 stream modes
├── langgraph_production.py      # v5.0 ProductionGraphBridge
├── production.py                # tenant RunStore / Queue / revisions / cancel
├── approval.py                  # application approval policy
├── durable.py                   # replay safety / reconcile contracts
├── trajectory_eval.py           # process-level Agent eval
└── ...

tests/
├── test_langgraph_basics.py
├── test_langgraph_tools_control.py
├── test_langgraph_persistence_interrupts.py
├── test_langgraph_store_subgraphs.py
├── test_langgraph_observability_production.py
└── ...
```

## v4.9 middleware and streaming boundary

`CallBudgetMiddleware` is a real LangChain `AgentMiddleware` with `before_model` / `after_model` hooks. It demonstrates why budget/logging/guardrail logic belongs in cross-cutting runtime policy rather than being copied into every business node.

`build_streaming_graph()` is a provider-free real LangGraph that emits v2 stream envelopes. `updates` exposes node updates, `values` exposes full state snapshots, and `custom` uses `get_stream_writer()` for business progress. Product streaming, operational telemetry and eval traces remain distinct consumers even when they originate from the same run.

## v5.0 production boundary

`ProductionGraphBridge` intentionally composes two state systems instead of pretending one replaces the other:

### LangGraph owns
- graph State / reducers / routing
- `thread_id`
- checkpoints and history
- `interrupt()` / `Command(resume=...)`
- Store / subgraphs / stream

### Application control plane owns
- tenant-scoped `run_id`
- product run status and optimistic revision
- queue claim / stale job and stale worker rejection
- cancellation semantics
- approval request identity and actor authorization
- mapping an authorized product run to its graph `thread_id`

### Infrastructure owns
- durable DB/checkpointer/Store implementations
- durable queue/broker
- worker lease / heartbeat / watchdog
- secrets, networking, scaling and telemetry backend

The bridge demonstrates the critical handshake: when LangGraph interrupts, the graph checkpoint id is written into the product RunRecord before entering `WAITING_APPROVAL`. An approval does not become `Command(resume=True)` until the application validates tenant, run, request id and actor authorization, then emits a new RESUME job. Duplicate queue deliveries are rejected by product revision before they advance the graph.

## Safety boundaries that remain true at v5.0

- `thread_id` is not an authorization token.
- Checkpoint persistence is not queue/worker CAS.
- `interrupt()` is not an approval policy.
- Graph replay does not create universal exactly-once side effects.
- Store namespaces do not replace tenant ACLs or memory write policy.
- Subgraphs do not automatically justify multi-agent architecture.
- Product cancellation is not the same as reaching Graph `END`.

## Next track

FastAPI. The next capability line will expose the existing v5.0 lifecycle through real HTTP contracts: create run, read status, stream progress, resolve approval and cancel safely.
