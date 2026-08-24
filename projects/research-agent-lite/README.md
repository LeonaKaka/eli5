# Research Assistant v2.8

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

Python closed at **Research Agent Lite v1.0**. LLM Application Engineering upgraded the same codebase to **Research Assistant v2.0**. The RAG track continues evolving that project.

Current project level: **v2.8**.

## RAG increments

- **v2.1** — `Document` / `DocumentBlock` / `DocumentParser`; structure, reading order and provenance are explicit
- **v2.2** — `ChunkPolicy` / `Chunk` / `StructureAwareChunker`; heading context, tables, overlap and stable ids
- **v2.3** — `EmbeddingProvider` / `EmbeddingService` / `EmbeddingRecord`; model id, dimension and normalization are part of the vector-space contract
- **v2.4** — `VectorIndex`, `ExactVectorIndex`, educational `ApproximateGraphIndex`; exact search is the correctness baseline for ANN recall
- **v2.5** — `BM25Index`, `RankedHit`, `HybridHit`, `reciprocal_rank_fusion`; lexical exact-match and dense ranking can be fused without assuming score calibration
- **v2.6** — `Reranker`, `RerankCandidate`, `RerankHit`, `RerankService`; first-stage rank and rerank score remain separately observable
- **v2.7** — `QueryStrategy`, `SearchQuery`, `QueryPlan`, `QueryPlanner`; original user query remains immutable while retrieval queries and synthesis needs are explicit
- **v2.8** — `EvidenceCandidate`, `EvidenceItem`, `EvidencePack`, `CitationRef`, `EvidencePacker`; token budget, per-source cap, near-duplicate suppression and provenance-derived citations are explicit

The project stays offline-first so architecture and tests remain deterministic. `DeterministicToyEmbeddingProvider`, `ApproximateGraphIndex`, `KeywordOverlapReranker`, and `RuleBasedTeachingQueryPlanner` are deliberately teaching implementations, not production semantic embedding, HNSW, cross-encoder, or LLM query-planning claims.

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
├── documents.py        # v2.1 structured ingestion
├── chunking.py         # v2.2 retrieval-unit policy
├── embeddings.py       # v2.3 embedding boundary
├── vector_index.py     # v2.4 exact + educational ANN
├── lexical.py          # v2.5 BM25 + RRF hybrid fusion
├── reranking.py        # v2.6 reranker contract
├── query_planning.py   # v2.7 rewrite / multi-query / decomposition plan
├── evidence.py         # v2.8 evidence packing + citation provenance
├── multimodal.py       # AssetRef / SourceRef provenance foundation
├── context.py          # context selection / budgeting
├── evals.py            # regression-gate foundation
└── ...

tests/
├── test_documents_chunking.py
├── test_embeddings_vector_index.py
├── test_lexical_reranking.py
├── test_query_evidence.py
└── ...
```

## Why query planning and evidence packing are explicit

A retrieval query is not the same thing as the user's original question, so `QueryPlan` preserves both. Likewise, a reranked hit is not yet trusted citation evidence, so `EvidencePacker` decides what fits the context while keeping `SourceRef` attached. This separation makes later retrieval and citation evals diagnosable.

## Next step

RAG 09–10 add retrieval metrics and end-to-end RAG evaluation. The final RAG system will separate retrieval failures from generation/citation failures and use the existing regression-gate layer to block regressions.
