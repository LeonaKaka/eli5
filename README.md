# ELI5 — AI Agent Engineering

Public static learning site for AI Agent engineering, built as an interactive ELI5 course rather than a glossary.

## Current tracks

### Python — 8/8 complete
- 01 Data, references, branching, loops, functions · Research Agent v0.1
- 02 Function contracts, type hints, Pydantic, schemas · v0.2
- 03 Modules, packages, imports, dependency direction, project structure · v0.3
- 04 HTTP, JSON, status codes, httpx, API clients · v0.4
- 05 async / await, event loop, gather, concurrency limits · v0.5
- 06 exceptions, retry/backoff, logging, fallback, idempotency · v0.6
- 07 class, dataclass, mutable defaults, composition, AgentState · v0.7
- 08 pytest, mock/fake, test layers, runnable Research Agent Lite · v1.0

### LLM Application Engineering — 10/10 complete
- 01 Model API / Request Lifecycle ✅
- 02 Messages / Instructions / Conversation State ✅
- 03 Tokens / Context Window / Context Engineering / Caching ✅
- 04 Generation & Reasoning Controls ✅
- 05 Streaming / TTFT / cancellation / partial output ✅
- 06 Structured Outputs / JSON Schema / Pydantic / refusal ✅
- 07 Tool / Function Calling / permission / execution boundary ✅
- 08 Multimodal / Files / asset lifecycle / provenance ✅
- 09 Model Routing / Cost / Latency / Reliability ✅
- 10 Evals / Prompt Lifecycle / Production Safety ✅

Full scope: `docs/llm-app-roadmap.md`.

## Teaching contract
Every lesson must include:
1. A concrete engineering problem first
2. A visual/explorable explanation
3. Code evolution rather than only final code
4. At least one failure/bug example
5. A continuous project increment
6. Exercises + interview-level checks

## Runnable project

`projects/research-agent-lite/` is the same project across both tracks. Python closed at v1.0; the LLM track evolves it into **Research Assistant v2.0**. It remains offline-first so tests are deterministic and no API key is required for the teaching architecture.

```bash
cd projects/research-agent-lite
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m app.main "RAG evaluation" --top-k 3
pytest -q
```

## Project evolution

- v1.0 — Python engineering baseline
- v1.1 — provider boundary / request lifecycle concepts
- v1.2 — conversation state and message history
- v1.3 — context builder + token budgeting
- v1.4 — generation / reasoning profiles
- v1.5 — explicit streaming state machine and partial-output semantics
- v1.6 — Pydantic structured-result contracts, validation and refusal shape
- v1.7 — provider-neutral ToolCall / ToolRegistry / ToolExecutor with schema + permission boundary
- v1.8 — AssetRef / SourceRef / PreparedAsset pipeline with size policy and provenance
- v1.9 — ModelRouter with capability gates, weighted priorities and explicit fallbacks
- v2.0 — EvalCase / EvalReport / RegressionGate with critical-slice regression blocking

## Next track

RAG: document parsing → chunking → embeddings → retrieval → hybrid search → reranking → citations → RAG evaluation.

## Pages
Deployed with GitHub Actions from the repository root. No build step, backend, or secret is required for the learning UI.
