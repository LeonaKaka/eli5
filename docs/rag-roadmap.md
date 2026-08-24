# RAG Engineering Roadmap

**Status: 10/10 complete · Research Assistant v3.0**

Scope: build a retrieval-augmented generation system whose evidence pipeline is inspectable, tunable and evaluable. The emphasis is not one framework or vector database; it is the engineering boundary from source asset to cited answer.

## 01 — Document Parsing / Document Model ✅
Asset vs Document vs Chunk, reading order, layout-aware parsing, OCR, tables/figures, parser abstraction, provenance and parser evaluation.

## 02 — Chunking ✅
Chunk size, overlap, semantic/structural boundaries, heading context, atomic tables/code/formulas, stable ids, policy versioning and downstream retrieval impact.

## 03 — Embeddings / Semantic Search ✅
Embedding intuition, vector geometry, cosine/dot/L2, normalization, model compatibility, batching, query/document asymmetry and semantic-search failure modes.

## 04 — Vector DB / Exact Search / ANN / HNSW ✅
Exact nearest-neighbor search, approximate search, HNSW graph intuition, recall-latency-memory trade-offs, metadata filters, index lifecycle and vector-store abstraction.

## 05 — Keyword / BM25 / Hybrid Search ✅
Lexical retrieval, BM25 intuition, dense vs sparse failure modes, hybrid fusion, RRF and exact-term/identifier queries.

## 06 — Reranking ✅
Recall-first retrieval vs precision-focused reranking, cross-encoder / LLM rerank concepts, top-k/top-n trade-offs, latency and rerank evaluation.

## 07 — Query Rewrite / Multi-query / Routing ✅
Rewrite ambiguous questions, decomposition, multi-query retrieval, query expansion, metadata routing, when rewriting hurts, and query-level observability.

## 08 — Citation / Provenance / Evidence Packing ✅
Chunk-to-source traceability, page/region citations, deduplication, evidence diversity, context packing, citation validation and user-facing evidence navigation.

## 09 — Retrieval Eval ✅
Golden query-document relevance sets, Recall@K, Precision@K, MRR, nDCG, hit rate, slice analysis and retrieval regression. No-answer queries use a separate abstention/false-positive contract rather than being mixed blindly into ranking metrics.

## 10 — End-to-End RAG Eval ✅
Separate retrieval vs evidence-packing vs generation vs citation failures; groundedness, citation correctness/completeness, trace-driven debugging, critical-slice regression gates and production feedback loops.

## Project evolution

`projects/research-agent-lite/` evolved from Research Assistant v2.0 to v3.0:
- v2.1 document model
- v2.2 chunking
- v2.3 embedding boundary
- v2.4 vector index
- v2.5 hybrid retrieval
- v2.6 reranker
- v2.7 query planner/rewriter
- v2.8 evidence packer + citations
- v2.9 retrieval eval suite
- v3.0 end-to-end RAG failure taxonomy and evaluation

## Next track

Agent Engineering: explicit agent loop, state transitions, stopping conditions, memory policy, planning, tool selection, guardrails, human approval and durable execution.
