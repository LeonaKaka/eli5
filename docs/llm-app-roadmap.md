# LLM Application Development Roadmap — COMPLETE

Scope: learn how to integrate foundation models into reliable products. RAG internals and multi-step Agent orchestration are taught in later skill tracks.

## 01 — Model API / Request Lifecycle ✅
REST vs SDK, auth, request/response objects, usage, error boundaries, provider abstraction.

## 02 — Messages / Instructions / Conversation State ✅
Instruction hierarchy, user/assistant messages, history, stateful vs stateless conversations, provider differences.

## 03 — Tokens / Context Window / Context Engineering ✅
Token accounting, input/output budgets, truncation, summarization, long context, context caching, relevance-first context design.

## 04 — Generation & Reasoning Controls ✅
Sampling/reasoning intent, max output, reproducibility, parameter defaults, model behavior trade-offs.

## 05 — Streaming ✅
SSE/event streams, delta events, TTFT, cancellation, partial failures, end events, UX vs total latency.

## 06 — Structured Outputs ✅
JSON Schema, Pydantic, strict output contracts, validation, refusals, invalid output, structured output vs plain JSON prompting.

## 07 — Tool / Function Calling ✅
Tool schema, call id, application-side execution, validation, tool result return, multiple/parallel calls, permission boundary. Complex agent loops are deferred to the Agent track.

## 08 — Multimodal / Files ✅
Images, PDFs, audio, file references vs inline data, preprocessing, modality limits, costs, provenance and asset lifecycle.

## 09 — Model Routing / Cost / Latency / Reliability ✅
Capability gates, weighted routing, fallback, task cost, latency percentiles, retries, circuit-breaker concepts, observability.

## 10 — Evals / Prompt Lifecycle / Production Safety ✅
Eval datasets, error taxonomy, deterministic checks, rubric/LLM-as-judge, human eval, regression gates, prompt/version management, traces, privacy, prompt-injection boundaries and secret handling.

## Final project — Research Assistant v2.0 ✅

`projects/research-agent-lite/` now contains provider-neutral boundaries for context building, generation profiles, streaming states, structured outputs, controlled tool execution, multimodal/file provenance, model routing and regression-gated evals.

The next track is RAG: parsing → chunking → embeddings → retrieval → hybrid search → reranking → citations → RAG eval.
