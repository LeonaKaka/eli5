# LangChain / LangGraph Roadmap

Scope: migrate Research Assistant v4.0 from a hand-built Agent control plane into framework-backed graph orchestration without forgetting the engineering boundaries already learned. LangChain provides model/tool/agent building blocks; LangGraph provides explicit stateful workflow orchestration, persistence and interrupts.

Current reference line: LangChain 1.3.x + LangGraph 1.2.x.

Current progress: **10 / 10 complete**, Research Assistant **v5.0**.

## 01 — LangChain vs LangGraph / Abstraction Ladder ✅
Understand `create_agent` versus `StateGraph`, how LangChain agents are implemented on top of LangGraph, and when a custom graph is justified.

## 02 — StateGraph Core / State / Nodes / Edges / Reducers ✅
Build a real `StateGraph`; define typed state, partial updates, reducers, `START` / `END`, fixed edges and conditional routing.

## 03 — LangChain Tools / ToolNode / Agent Loop ✅
Use `@tool`, `ToolNode`, `ToolMessage` and `tools_condition`; preserve tool-call/result correlation and understand the standard model ↔ tools loop.

## 04 — Conditional Control Flow / Command / Send ✅
Use conditional edges, `Command(update + goto)` and `Send` dynamic fan-out/map-reduce with reducer-based fan-in.

## 05 — Persistence / Threads / Checkpointers ✅
Use a checkpointer, `thread_id`, StateSnapshot inspection/history, update-state, replay/time-travel and fault-recovery semantics.

## 06 — Interrupt / Human-in-the-loop / Resume ✅
Use `interrupt()` and `Command(resume=...)` for durable HITL and preserve replay-safe side-effect boundaries.

## 07 — Memory / Store ✅
Separate thread-scoped checkpoints from cross-thread Store data, use Runtime context + namespace scope, and preserve application write policy/invalidation.

## 08 — Subgraphs / Multi-Agent / Handoff ✅
Compose shared/private subgraphs, choose persistence scope and use `Command.PARENT` for minimal-context handoffs.

## 09 — LangChain Middleware / Streaming / Observability ✅
Use real `AgentMiddleware` hook contracts for cross-cutting model-call policy and real LangGraph v2 `updates` / `values` / `custom` streaming. Separate product streaming, operational telemetry and trajectory/eval traces.

## 10 — Production LangGraph Architecture ✅
Close the project with `ProductionGraphBridge`, combining LangGraph thread/checkpoint/interrupt execution with the existing tenant-scoped product `RunStore` / Queue / optimistic revision / cancellation / approval-authorization control plane. Explicitly preserve the boundary between framework runtime, application control and infrastructure.

## Project evolution
- v4.1 abstraction mapping + first compiled LangGraph ✅
- v4.2 typed StateGraph + reducers + routing ✅
- v4.3 tools / ToolNode / create_agent comparison ✅
- v4.4 Command / Send / conditional orchestration ✅
- v4.5 checkpointers / threads / persistence ✅
- v4.6 interrupts / human-in-the-loop resume ✅
- v4.7 Store / long-term memory ✅
- v4.8 subgraphs / multi-agent handoffs ✅
- v4.9 middleware / streaming / observability ✅
- v5.0 production LangGraph architecture ✅

## Final boundary
Do not treat the framework as magic. LangGraph now owns graph-level state, routing, persistence, interrupts, Store integration, subgraphs and streaming. It does not make `thread_id` an authorization token, replace product run revisions or queue worker leases, define who may approve side effects, guarantee exactly-once external actions, or remove tenant/memory/permission policy.

## Next track
FastAPI: expose the v5.0 run lifecycle through real service contracts for create/status/stream/approval/cancel.
