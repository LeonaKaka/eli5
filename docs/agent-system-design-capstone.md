# Deep Research Agent — Final System Design Capstone

Status: **Advanced A6 / Research Assistant v7.0**.

## Product requirement

Design a multi-tenant Deep Research Agent for roughly **1,000 concurrent users**. One Run may last up to **hours** and may use web browsing, RAG, MCP capabilities, files, generated Python, shell utilities, human approval and external side effects. The service must survive Worker restarts, tolerate duplicate Queue delivery, resume from checkpoints, isolate tenants, bound overload/cost, stream progress to clients and provide enough observability/evaluation to diagnose regressions.

The number “1,000 users” is a capacity envelope, not a requirement for 1,000 Workers. Admission, quotas, active execution concurrency and queued work are separate controls.

## Final topology

```text
Browser / Mobile / API Client
            │
            ▼
      Load Balancer
            │
     ┌──────┴──────┐
     ▼             ▼
 FastAPI API    FastAPI API     stateless request tier
     │             │
     └──────┬──────┘
            │ authenticate / authorize / validate commands
            ▼
        RunStore  ◄──────────── authoritative product Run truth
            │
            ├──────── Event Store ──────► SSE projection / replay
            │
            └──────── Queue ────────────► at-least-once delivery
                                          │
                         ┌────────────────┼────────────────┐
                         ▼                ▼                ▼
                      Worker A         Worker B         Worker N
                         │                │                │
                         └──── Lease / Heartbeat / Fence ─┘
                                          │
                                          ▼
                                       LangGraph
                                  graph state / checkpoint
                                          │
                   ┌──────────────────────┼───────────────────────┐
                   ▼                      ▼                       ▼
                  RAG                  MCP tools              Tool Runtime
                                                                  │
                                                   Browser / Files / Sandbox
                                                   Python / Shell / Artifacts
                                                                  │
                                          Security Policy / Approval boundary
                                                                  │
                                                         External systems
                                                   idempotency / reconcile

Cross-cutting:
- Observability: metrics + traces + failure clusters
- Eval: golden regressions + sampled online quality checks
- Audit: identity / approval / sensitive actions
- Object storage: durable user files and artifacts
```

## Ownership contract

| Concern | Owner | Why it is not another component |
| --- | --- | --- |
| Identity | Identity provider / auth layer | Prompt text and tenant headers are not identity proof |
| Product Run truth | RunStore | Queue and checkpoints are partial execution records |
| Delivery | Queue | Delivery is not ownership or authoritative Run state |
| Current execution ownership | Lease coordinator + fencing | Queue pop/ack cannot stop a zombie Worker |
| Graph continuation | LangGraph checkpointer | Checkpoint does not authorize a tenant or Worker |
| Tool authority | Host security policy | LLM/MCP capability discovery cannot grant permission |
| Hostile-code isolation | Sandbox | cwd/path helpers or a same-user subprocess are not a security boundary |
| Durable artifacts | Object storage | Prompt context and Worker local disk are not durable artifact truth |
| Client incremental events | Event store / SSE projection | Event stream is rebuildable from authoritative Run state |
| Operational health | Observability pipeline | A trace is not quality truth |
| Quality truth | Eval pipeline | HTTP 200 does not mean a good research answer |
| Side-effect safety | Idempotency/fencing/reconciliation contract | Queue “exactly once” cannot cover arbitrary external APIs |

## One Run lifecycle

```text
POST /runs
→ authenticate Principal
→ derive tenant / authorize create
→ admission + quota + cost budget
→ RunStore: QUEUED + revision
→ enqueue logical attempt
→ return 202/201 contract

Worker receives delivery
→ tenant/run/attempt validation
→ claim lease + fencing token
→ RunStore: RUNNING
→ LangGraph invoke/resume from checkpoint
→ retrieve / MCP / Browser / sandboxed Python
→ security policy checks proposed sensitive actions
→ optional interrupt + exact human approval
→ checkpoint durable progress
→ publish sanitized client events
→ persist final Run state
→ release ownership
```

The HTTP request never owns the hours-long Agent execution.

## Recovery invariants

### Worker crash

Detect lease expiry, requeue from the latest durable checkpoint, let a new Worker acquire a higher fencing token, and reject the old zombie Worker if it wakes up.

### Duplicate Queue delivery

Treat delivery as at-least-once. Idempotent claim accepts at most one current owner; duplicate/stale attempts do not execute a second Agent.

### Malicious Browser/RAG/file content

Mark external content untrusted. It may influence model reasoning, but product `RunAuthority` controls capability, egress, secret access and approval. Generated hostile code still requires a real sandbox.

### RunStore unavailable

Fail readiness and stop accepting state-changing work that cannot be durably recorded. Never reconstruct authoritative product state from Queue deliveries or LangGraph checkpoints alone.

### SSE disconnect

Do not cancel the Run. Reconnect with `Last-Event-ID`; if the event retention window is gone, fetch current Run truth and establish a new event-stream baseline.

### Ambiguous side effect

If an action may already have affected an external system, reuse a committed result when known, retry only when the replay contract permits it, otherwise reconcile external reality before continuing.

### Quality regression

Compare current traffic/evals against a baseline. Use per-layer traces/metrics to locate operational regressions and explicit evals to catch answer/evidence regressions when all spans are technically successful.

### Overload

Apply global and per-tenant admission limits before Queue growth becomes unbounded. Return explicit retry guidance, protect downstream budgets, then scale the measured bottleneck rather than blindly adding Workers.

## Capacity decisions

A reference teaching envelope may begin with:

```text
~1000 concurrent users
API replicas: >= 2
Worker replicas: workload dependent
max Run duration: 6 h
finite global queue depth
finite tenant inflight quota
per-Run token/tool/time/cost budgets
```

Worker count is driven by active workload and downstream limits, not user count alone. Browser/Python jobs may need separate Worker pools because their CPU/RAM/process profile differs from lightweight retrieval/model orchestration.

## Deployment mapping (illustrative, not mandatory)

The architecture is about contracts, not vendor names. One possible implementation could map:

```text
FastAPI replicas                 → container/service runtime
RunStore / approval / revisions  → transactional shared database
Queue / admission counters       → durable queue / shared coordination service
LangGraph checkpoints            → persistent checkpointer backend
Artifacts                        → object storage
Browser/Python                   → dedicated sandbox Worker pool
Events                           → retained shared event backend
Telemetry                        → OpenTelemetry-compatible pipeline
```

Postgres, Redis, Docker, managed queues and cloud runtimes are implementation options when their contract fits; none is the architecture by itself.

## Final review questions

1. Why does `POST /runs` enqueue instead of running the Agent inline?
2. Why are RunStore, Queue and LangGraph checkpoint three different pieces of state?
3. What stops two Workers from executing the same Run after duplicate delivery?
4. Why does a lease need fencing against zombie Workers?
5. What does the system do with an `IN_FLIGHT` non-idempotent external action after a crash?
6. Why is MCP discovery not authorization?
7. Why is Browser content always data rather than authority?
8. Why is a Python subprocess with a timeout not a security sandbox?
9. How does a disconnected SSE client catch up without owning the Run?
10. Why can all spans be green while quality is red?
11. Where do per-tenant quotas and cost budgets apply?
12. What happens when RunStore is unavailable?
13. How do you deploy a new Worker version without killing hours-long Runs?
14. Which information belongs in traces, which belongs in audit, and which should never be logged by default?
15. Why is “exactly once” an end-to-end side-effect contract rather than a Queue checkbox?

If these questions can be answered by naming the owner, failure mode and recovery invariant—not by naming a framework—the course objective is complete.
