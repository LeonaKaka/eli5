# Research Assistant v2.4

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

The eight Python lessons closed at **Research Agent Lite v1.0**. The ten LLM Application Engineering lessons upgraded the same codebase into **Research Assistant v2.0**. The RAG track keeps evolving that project instead of starting another demo.

Current project level: **v2.4**.

## RAG increments

- **v2.1** — `BlockType`, `DocumentBlock`, `Document`, `DocumentParser`; parsed content has explicit reading order, block type and `SourceRef` provenance
- **v2.2** — `ChunkPolicy`, `Chunk`, `StructureAwareChunker`; heading context, atomic tables, overlap, stable ids and policy version are explicit
- **v2.3** — `EmbeddingProvider`, `EmbeddingService`, `EmbeddingRecord`; model id, dimension and normalization become part of the vector-space contract
- **v2.4** — `VectorIndex`, `ExactVectorIndex`, `ApproximateGraphIndex`; exact search becomes the correctness baseline and educational ANN exposes the candidate-budget/recall trade-off

The project remains offline-first so architecture and tests stay deterministic. `DeterministicToyEmbeddingProvider` is deliberately not a semantic embedding model, and `ApproximateGraphIndex` is deliberately not presented as production HNSW.

## Run

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

python -m app.main "RAG evaluation"
pytest -q
```

## RAG structure

```text
app/
├── documents.py       # v2.1 structured document ingestion model
├── chunking.py        # v2.2 structure-aware chunk policy
├── embeddings.py      # v2.3 provider-neutral embedding boundary + vector math
├── vector_index.py    # v2.4 exact baseline + educational graph ANN
├── multimodal.py      # AssetRef / SourceRef provenance foundation
├── context.py         # context selection and budgeting
├── evals.py           # regression gates reused by retrieval evals later
└── ...

tests/
├── test_documents_chunking.py
├── test_embeddings_vector_index.py
└── ...
```

## Why exact search stays in the project

ANN quality should be measured against a correctness baseline. `ExactVectorIndex` is intentionally simple and slow: it lets later retrieval tests ask whether an approximate index preserved enough of the true top-k set. This is also why `recall_at_k()` is already present before the dedicated retrieval-eval lessons.

## Next step

RAG 05–06 add lexical BM25-style retrieval, dense+sparse hybrid fusion and reranking. Those layers will consume the same `Chunk` ids and return traceable `SearchHit` objects instead of inventing another document representation.
