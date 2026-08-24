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

### RAG Engineering — 4/10 live
- 01 Document Parsing / Document Model / reading order / OCR / provenance ✅
- 02 Chunking / overlap / structure-aware boundaries / stable chunk ids ✅
- 03 Embeddings / cosine / dot / L2 / model compatibility / batching ✅
- 04 Vector DB / Exact Search / ANN / HNSW / metadata filtering ✅
- 05 BM25 / Hybrid Search
- 06 Reranking
- 07 Query Rewrite / Multi-query
- 08 Citation / Provenance
- 09 Retrieval Eval
- 10 End-to-End RAG Eval

Full scope: `docs/rag-roadmap.md`.

## Teaching contract
Every lesson must include:
1. A concrete engineering problem first
2. A visual/explorable explanation
3. Code evolution rather than only final code
4. At least one failure/bug example
5. A continuous project increment
6. Exercises + interview-level checks

## Runnable project

`projects/research-agent-lite/` is the same project across all tracks. Python closed at v1.0, LLM at v2.0, and RAG now evolves it through structured ingestion, embedding and retrieval-index boundaries.

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
- v1.1–v2.0 — LLM application engineering boundaries, routing and evals
- v2.1 — `Document`, `DocumentBlock`, `BlockType`, `DocumentParser`
- v2.2 — `ChunkPolicy`, `Chunk`, `StructureAwareChunker`
- v2.3 — `EmbeddingProvider`, `EmbeddingService`, versioned `EmbeddingRecord`
- v2.4 — `VectorIndex`, `ExactVectorIndex`, educational `ApproximateGraphIndex`, ANN recall baseline

The offline toy embedding and graph ANN are teaching adapters, not claims of production semantic quality or a production HNSW implementation.

## Pages
Deployed with GitHub Actions from the repository root. No build step, backend, or secret is required for the learning UI.
