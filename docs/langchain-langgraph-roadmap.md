# LangChain / LangGraph Roadmap

Scope: migrate Research Assistant v4.0 from a hand-built Agent control plane into framework-backed graph orchestration without forgetting the engineering boundaries already learned. LangChain provides model/tool/agent building blocks; LangGraph provides explicit stateful workflow orchestration, persistence and interrupts.

Current reference line: LangChain 1.3.x + LangGraph 1.2.x.

Current progress: **08 / 10 live**, Research Assistant **v4.8**.

## 01 — LangChain vs LangGraph / Abstraction Ladder ✅
Understand `create_agent` versus `StateGraph`, how LangChain agents are implemented on top of LangGraph, what problems each abstraction solves, when a simple `create_agent` is enough, when a custom graph is justified, and how the existing v4.0 AgentLoop maps onto graph concepts.

## 02 — StateGraph Core / State / Nodes / Edges / Reducers ✅
Build a real `StateGraph`; define typed state, partial state updates, `START` / `END`, fixed edges, conditional routing and reducers. Learn why state is not conversation history and why reducers are merge semantics rather than convenience helpers.

## 03 — LangChain Tools / ToolNode / Agent Loop ✅
Use `@tool`, `ToolNode`, `ToolMessage`, `tools_condition` and tool routing. Inspect the ReAct-style model ↔ tools loop, preserve tool-call/result correlation, and compare custom `StateGraph` control with LangChain `create_agent`.

## 04 — Conditional Control Flow / Command / Send ✅
Model branches and loops with conditional edges, use `Command` to combine state update + routing, use `Send` for dynamic fan-out/map-reduce, and connect these APIs to the ActionGraph / orchestration concepts from Agent 05. Reducers define fan-in semantics; dynamic fan-out does not remove concurrency/rate-limit policy.

## 05 — Persistence / Threads / Checkpointers ✅
Use a checkpointer, `thread_id`, state history, checkpoint inspection, replay/time-travel concepts and fault recovery. Separate thread-scoped graph state from external run-control state.

## 06 — Interrupt / Human-in-the-loop / Resume ✅
Use `interrupt()` and `Command(resume=...)` for durable pauses, approval/edit/review flows, and understand why effects before an interrupt must be idempotent or externally reconciled.

## 07 — Memory / Store ✅
Separate short-term thread state persisted by checkpointers from long-term cross-thread data persisted in a Store. Use runtime context and namespace tuples for user/workspace scope, while preserving application write policy, sensitive-data rejection and explicit invalidation.

## 08 — Subgraphs / Multi-Agent / Handoff ✅
Compose shared-state subgraphs directly, wrap private/different schemas with explicit input/output mapping, choose per-invocation/per-thread/stateless subgraph persistence, and use `Command.PARENT` for minimal-context handoffs to sibling parent nodes.

## 09 — LangChain Middleware / Streaming / Observability
Use LangChain middleware hooks, dynamic model/tool policies, retries and guardrails; stream graph updates/values/events; connect structured traces to trajectory eval and debugging.

## 10 — Production LangGraph Architecture
Migrate the Research Assistant runtime into a graph-backed architecture while preserving tenant scope, run revision, approval, cancellation and replay-safety boundaries. Identify which responsibilities LangGraph can provide and which remain application/infrastructure concerns. Close the project at Research Assistant v5.0.

## Project evolution
Continue `projects/research-agent-lite/` from Research Assistant v4.0:
- v4.1 abstraction mapping + first compiled LangGraph ✅
- v4.2 explicit typed StateGraph + reducers + routing ✅
- v4.3 LangChain tools / ToolNode / create_agent comparison ✅
- v4.4 Command / Send / conditional orchestration ✅
- v4.5 checkpointers / threads / persistence ✅
- v4.6 interrupts / human-in-the-loop resume ✅
- v4.7 Store / long-term memory ✅
- v4.8 subgraphs / multi-agent handoffs ✅
- v4.9 middleware / streaming / observability
- v5.0 production LangGraph architecture

## Teaching rule
Do not treat the framework as magic. Every LangGraph abstraction should be mapped back to an engineering problem already implemented manually in v4.0. Framework behavior that affects durability, replay, side effects, permissions or tenant isolation must be stated explicitly rather than assumed.
