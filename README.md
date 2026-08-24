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

### RAG Engineering — 6/10 live
- 01 Document Parsing / Document Model / OCR / provenance ✅
- 02 Chunking / overlap / structure-aware boundaries / stable ids ✅
- 03 Embeddings / cosine / dot / L2 / model compatibility ✅
- 04 Vector DB / Exact / ANN / HNSW / filters ✅
- 05 BM25 / lexical retrieval / RRF hybrid fusion ✅
- 06 Reranking / candidate recall / two-stage retrieval ✅
- 07 Query Rewrite / Multi-query
- 08 Citation / Evidence Packing
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

`projects/research-agent-lite/` is the same project across all tracks. Python closed at v1.0, LLM at v2.0, and RAG is now at **v2.6**.

```bash
cd projects/research-agent-lite
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m app.main "RAG evaluation" --top-k 3
pytest -q
```

## Current RAG project increments

- v2.1 — structured `Document` ingestion boundary
- v2.2 — structure-aware `ChunkPolicy` / `Chunk`
- v2.3 — `EmbeddingProvider` / versioned vector-space contract
- v2.4 — Exact baseline + educational graph ANN
- v2.5 — real offline BM25 baseline + `reciprocal_rank_fusion()`
- v2.6 — `Reranker` boundary with first-stage rank preserved through reranking

The toy embedding, graph ANN and keyword-overlap reranker are deterministic teaching adapters. They validate architecture and failure boundaries offline; they are not presented as production semantic models, HNSW, or cross-encoders.

## Pages
Deployed with GitHub Actions from the repository root. No build step, backend, or secret is required for the learning UI.
