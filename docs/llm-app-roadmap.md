# LLM Application Development Roadmap

Scope: learn how to integrate foundation models into reliable products. RAG internals and multi-step Agent orchestration are taught in later skill tracks.

## 01 — Model API / Request Lifecycle
REST vs SDK, auth, request/response objects, usage, error boundaries, provider abstraction.

## 02 — Messages / Instructions / Conversation State
Instruction hierarchy, user/assistant messages, history, stateful vs stateless conversations, provider differences.

## 03 — Tokens / Context Window / Context Engineering
Token accounting, input/output budgets, truncation, summarization, long context, context caching, relevance-first context design.

## 04 — Generation & Reasoning Controls
Temperature/top-p, max output, reasoning controls, reproducibility, parameter defaults, model behavior trade-offs.

## 05 — Streaming
SSE/event streams, delta events, TTFT, cancellation, partial failures, end events, UX vs total latency.

## 06 — Structured Outputs
JSON Schema, Pydantic, strict output contracts, validation, refusals, invalid output, structured output vs plain JSON prompting.

## 07 — Tool / Function Calling
Tool schema, call id, application-side execution, validation, tool result return, multiple/parallel calls, tool choice. Complex agent loops are deferred to the Agent track.

## 08 — Multimodal / Files
Images, PDFs, audio, file references vs inline data, preprocessing, modality limits, costs, provenance.

## 09 — Model Selection / Cost / Latency / Reliability
Model routing, fallback, cached inputs, token costs, batching, timeouts, retries, rate limits, provider abstraction, observability.

## 10 — Evals / Prompt Lifecycle / Production Safety
Golden datasets, error taxonomy, deterministic checks, LLM-as-judge, human eval, regression, prompt/version management, traces, A/B tests, privacy, prompt-injection boundaries and secret handling.

## Final project
Upgrade `projects/research-agent-lite/` into a provider-abstracted Research Assistant v2.0 with streaming, structured outputs, one controlled tool call, model routing, usage accounting and an eval suite.
