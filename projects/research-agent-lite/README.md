# Research Assistant v4.8

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

Python closed at **Research Agent Lite v1.0**. LLM Application Engineering upgraded the same codebase to **Research Assistant v2.0**. RAG closed at **Research Assistant v3.0**. Agent Engineering closed at **Research Assistant v4.0**. The LangChain / LangGraph track now migrates the same project toward v5.0.

Current project level: **v4.8**.

## Framework track increments

- **v4.1** — first real compiled `StateGraph`
- **v4.2** — typed graph state, reducers, fixed/conditional edges and branch rejoin
- **v4.3** — `@tool search_papers`, `ToolNode`, `tools_condition`, real `AIMessage.tool_calls` and correlated `ToolMessage.tool_call_id`
- **v4.4** — `Command(update=..., goto=...)` and `Send` dynamic fan-out/map-reduce with reducer-based fan-in
- **v4.5** — `PersistenceState`, `InMemorySaver`, `thread_config()`, real thread-scoped checkpoints, `get_state()`, `get_state_history()` and `update_state()`
- **v4.6** — `ApprovalState`, real `interrupt()` + `Command(resume=...)`, safe approval graph and deliberately unsafe pre-interrupt replay demo
- **v4.7** — `MemoryContext`, `InMemoryStore`, `Runtime[MemoryContext]`, namespace design, cross-thread recall, `MemoryWritePolicy` gating and explicit invalidation
- **v4.8** — shared-state subgraph composition, private-state wrapper mapping, and deterministic subgraph → parent sibling handoff with `Command.PARENT`

The project depends on `langchain>=1.3,<2` and `langgraph>=1.2,<2`. Lessons 01–08 do not call any external model provider and therefore do not require an API key.

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
├── langgraph_store.py           # v4.7 Store, Runtime context, namespace + memory policy
├── langgraph_subgraphs.py       # v4.8 shared/private subgraphs + Command.PARENT handoff
├── memory.py                    # application memory kinds, scope, write gate, invalidation
├── production.py                # tenant RunStore, Queue, worker revisions, cancel/requeue/resume
└── ...

tests/
├── test_langgraph_basics.py
├── test_langgraph_tools_control.py
├── test_langgraph_persistence_interrupts.py
├── test_langgraph_store_subgraphs.py
└── ...
```

## Store boundary

The checkpointer persists graph state inside one `thread_id`; the Store persists application-defined items across threads. v4.7 compiles a graph with both an `InMemorySaver` and an `InMemoryStore`, and injects `user_id/workspace_id` through a typed Runtime context. User/workspace namespace design is explicit.

The Store is **not** the policy layer. Writes still pass through the original `MemoryWritePolicy`: sensitive data, working memory, unverified semantic facts, low-confidence information, or data without demonstrated cross-run reuse value can be rejected. Run-scoped information is kept in thread/checkpoint state rather than promoted into the cross-thread Store.

The adapter also rejects silent reuse of the same memory key. Corrections use an explicit invalidation path instead of silently changing an old memory's meaning. A real production store may additionally need immutable versions/audit history.

## Subgraph boundary

v4.8 demonstrates three different composition contracts:

1. **Shared state keys** — a compiled subgraph can be passed directly to `add_node`; shared channels flow between parent and child while child-only scratch does not become parent business state.
2. **Different/private schemas** — a wrapper node explicitly maps parent input into child state and maps only selected child output back.
3. **Parent handoff** — a retriever subgraph returns `Command(graph=Command.PARENT, goto="writer_agent", update=...)`, passing a minimal handoff payload to a sibling parent node instead of copying all private scratch/history.

Subgraph persistence is a separate choice: default `checkpointer=None` is per-invocation, `True` is per-thread persistent child state, and `False` is stateless. Per-thread subgraphs require care with parallel calls because multiple writes to the same child checkpoint namespace can conflict.

## What still remains outside the framework

Store namespaces do not replace tenant authorization. Subgraph routing does not replace ownership/capability policy. `Command.PARENT` does not automatically validate handoff context or preserve tool-call message pairs. Product RunStore/Queue/lease/cancellation semantics, side-effect replay safety, approval policy and regression gates remain explicit application/infrastructure contracts.

## Next step

LangChain / LangGraph 09–10 add middleware, streaming/observability, then reconcile the framework runtime with the v4.0 production control plane and close Research Assistant at v5.0.
