# ELI5 — AI Agent Engineering

Public static learning site for AI Agent engineering, built as an interactive ELI5 course rather than a glossary.

## Current tracks

### Python — 8/8 complete
- 01 Data, references, branching, loops, functions
- 02 Function contracts, type hints, Pydantic, schemas
- 03 Modules, packages, imports, dependency direction
- 04 HTTP, JSON, status codes, API clients
- 05 async / await, event loop, concurrency limits
- 06 exceptions, retry/backoff, logging, fallback, idempotency
- 07 class, dataclass, composition, AgentState
- 08 pytest, mock/fake, runnable Research Agent Lite v1.0

### LLM Application Engineering — 10/10 complete
API lifecycle → conversation state → context → generation → streaming → structured output → tool calling → multimodal/files → routing/reliability → evals/safety.

Full scope: `docs/llm-app-roadmap.md`.

### RAG Engineering — 10/10 complete
Document parsing → chunking → embeddings → ANN/HNSW → BM25/hybrid → reranking → query planning → evidence/citation → retrieval eval → end-to-end RAG eval.

Full scope: `docs/rag-roadmap.md`.

### Agent Engineering — 8/10 live
- 01 Agent Loop / observe → decide → act → update → stop/continue ✅
- 02 State Machine / Stop Conditions / Run Budgets / LoopGuard ✅
- 03 Planning / Replanning / dependencies / progress / plan drift ✅
- 04 Memory Architecture / write policy / scope / contamination / invalidation ✅
- 05 Multi-step Tool Orchestration / dependency graph / parallel / fan-in / partial failure ✅
- 06 Human-in-the-loop / Guardrails / exact-call approval / interrupt / least privilege ✅
- 07 Recovery / Durable Execution / checkpoint / replay safety / reconciliation ✅
- 08 Multi-Agent / Handoff / Supervisor / ownership / cycle guard ✅
- 09 Observability / Trajectory Eval
- 10 Production Agent Architecture

Full scope: `docs/agent-roadmap.md`.

## Teaching contract
Every lesson must include:
1. A concrete engineering problem first
2. A visual/explorable explanation
3. Code evolution rather than only final code
4. At least one failure/bug example
5. A continuous project increment
6. Exercises + interview-level checks

## Runnable project

`projects/research-agent-lite/` is the same project across all tracks. Python closed at v1.0, LLM at v2.0, RAG at v3.0, and the Agent track is now at **Research Assistant v3.8**.

```bash
cd projects/research-agent-lite
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

## Current Agent project increments

- v3.1 — `AgentDecision`, `AgentObservation`, `AgentContext`, `AgentLoop`, `AgentRunResult`, trajectory trace
- v3.2 — `RunStatus`, `StopReason`, `RunBudget`, `AgentControlState`, `LoopGuard`
- v3.3 — `Plan`, `PlanStep`, `ProgressSignal`, `ReplanPolicy`, revision-preserving replans
- v3.4 — `MemoryWritePolicy`, `MemoryStore`, scoped memory, invalidation and bilingual deterministic retrieval baseline
- v3.5 — `ActionGraph`, `ActionNode`, `ToolOrchestrator`, dependency waves, output bindings and partial-result joins
- v3.6 — `ApprovalPolicy`, `ApprovalRequest`, `ApprovalManager`; exact ToolCall approval, `WAITING_APPROVAL`, single-use resume and destructive-action policy
- v3.7 — `DurableAction`, `DurableCheckpoint`, `DurableActionRunner`, `RecoveryDecision`; PREPARED/IN_FLIGHT/COMMITTED are explicit and ambiguous non-idempotent recovery requires reconciliation
- v3.8 — `AgentDirectory`, `SupervisorRouter`, `HandoffContract`, `HandoffGuard`, `HandoffCoordinator`; capability routing, explicit ownership, typed artifacts and circular delegation protection

The Agent track deliberately keeps planning, execution, memory, approval, recovery and handoff boundaries separate. A model may propose actions or delegations, but dependency execution, concurrency, side-effect policy, replay safety, ownership and hard stops remain application-side controls.

Durable execution does **not** claim universal exactly-once semantics. A process can crash after an external side effect but before a committed checkpoint; non-idempotent IN_FLIGHT actions therefore require reconciliation unless the external service genuinely supplies an idempotency contract.

Framework-specific orchestration is intentionally deferred. LangGraph comes in the next capability track after the underlying loop/state/checkpoint problems are understood.

## Pages
Deployed with GitHub Actions from the repository root. No build step, backend, or secret is required for the learning UI.
