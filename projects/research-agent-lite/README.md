# Research Assistant v2.2

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

The eight Python lessons closed at **Research Agent Lite v1.0**. The ten LLM Application Engineering lessons upgraded the same codebase into **Research Assistant v2.0**. The RAG track now keeps evolving that project instead of starting another demo.

Current project level: **v2.2**.

## What is already inside

Python + LLM layers provide validated boundaries, async execution, retry/fallback, state, structured outputs, streaming state, tool permission, asset provenance, model routing and regression gates.

## RAG increments

- **v2.1** — `BlockType`, `DocumentBlock`, `Document`, `DocumentParser`; parsed content has explicit reading order, block type and `SourceRef` provenance
- **v2.2** — `ChunkPolicy`, `Chunk`, `StructureAwareChunker`; heading context, atomic tables, overlap, stable ids and policy version are explicit

The project remains offline-first so architecture and tests stay deterministic. Real parser/embedding/vector-store adapters arrive only after the core interfaces are clear.

## Run

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

python -m app.main "RAG evaluation"
pytest -q
```

## Structure

```text
app/
├── models.py
├── state.py
├── errors.py
├── sources.py
├── agent.py
├── context.py
├── generation.py
├── streaming.py
├── structured.py
├── tools.py
├── multimodal.py
├── routing.py
├── evals.py
├── documents.py     # v2.1 structured document ingestion model
├── chunking.py      # v2.2 structure-aware chunk policy
└── main.py

tests/
├── test_state.py
├── test_agent.py
├── test_context_generation.py
├── test_streaming_structured.py
├── test_tools_multimodal.py
├── test_routing_evals.py
└── test_documents_chunking.py
```

## Why parsing and chunking are separate

`DocumentParser` converts an asset into a stable document model with structure and provenance. `StructureAwareChunker` consumes that model and decides retrieval units. This keeps parser replacement independent from chunking experiments and makes downstream retrieval evaluation meaningful.

## Next step

RAG 03–04 will add embedding boundaries and a vector-index abstraction, then teach exact search vs ANN/HNSW before any specific vector database becomes the center of the design.
