# Research Assistant v2.6

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

Python closed at **Research Agent Lite v1.0**. LLM Application Engineering upgraded the same codebase to **Research Assistant v2.0**. The RAG track continues evolving that project.

Current project level: **v2.6**.

## RAG increments

- **v2.1** — `Document` / `DocumentBlock` / `DocumentParser`; structure, reading order and provenance are explicit
- **v2.2** — `ChunkPolicy` / `Chunk` / `StructureAwareChunker`; heading context, tables, overlap and stable ids
- **v2.3** — `EmbeddingProvider` / `EmbeddingService` / `EmbeddingRecord`; model id, dimension and normalization are part of the vector-space contract
- **v2.4** — `VectorIndex`, `ExactVectorIndex`, educational `ApproximateGraphIndex`; exact search is the correctness baseline for ANN recall
- **v2.5** — `BM25Index`, `RankedHit`, `HybridHit`, `reciprocal_rank_fusion`; lexical exact-match and dense ranking can be fused without assuming score calibration
- **v2.6** — `Reranker`, `RerankCandidate`, `RerankHit`, `RerankService`; first-stage rank and rerank score remain separately observable

The project stays offline-first so architecture and tests remain deterministic. `DeterministicToyEmbeddingProvider`, `ApproximateGraphIndex`, and `KeywordOverlapReranker` are deliberately teaching implementations, not production semantic embedding, HNSW, or cross-encoder claims.

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
├── documents.py       # v2.1 structured ingestion
├── chunking.py        # v2.2 retrieval-unit policy
├── embeddings.py      # v2.3 embedding boundary
├── vector_index.py    # v2.4 exact + educational ANN
├── lexical.py         # v2.5 BM25 + RRF hybrid fusion
├── reranking.py       # v2.6 reranker contract
├── multimodal.py      # AssetRef / SourceRef provenance
├── context.py         # context selection / budgeting
├── evals.py           # regression-gate foundation
└── ...

tests/
├── test_documents_chunking.py
├── test_embeddings_vector_index.py
├── test_lexical_reranking.py
└── ...
```

## Why retrieval and reranking remain separate

First-stage retrieval is optimized for candidate recall over a large corpus. Reranking is optimized for precision over a much smaller candidate set. Keeping those stages separate lets tests diagnose whether a relevant chunk was never recalled or was recalled but ranked too low.

## Next step

RAG 07–08 add query rewriting/decomposition and evidence packing with citation provenance. Those modules will reuse the same chunk ids, retrieval traces and `SourceRef` chain instead of creating a second evidence representation.
