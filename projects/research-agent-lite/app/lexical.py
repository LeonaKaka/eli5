from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from pydantic import BaseModel, Field

from .chunking import Chunk

_TOKEN_RE = re.compile(r"[A-Za-z0-9_.:/-]+|[\u4e00-\u9fff]+")


def tokenize(text: str) -> list[str]:
    """Small deterministic tokenizer for the offline teaching baseline.

    It deliberately preserves identifier-like strings such as CUDA_ERROR_700,
    DOI fragments, paths and hyphenated model names better than whitespace
    splitting. Production lexical search should use language/domain-appropriate
    analyzers rather than assuming this tokenizer is universal.
    """
    return [match.group(0).lower() for match in _TOKEN_RE.finditer(text)]


class RankedHit(BaseModel):
    id: str = Field(min_length=1)
    score: float
    rank: int = Field(ge=1)
    retriever: str = Field(min_length=1)
    metadata: dict[str, str] = Field(default_factory=dict)


class HybridHit(BaseModel):
    id: str = Field(min_length=1)
    score: float
    ranks: dict[str, int] = Field(default_factory=dict)
    metadata: dict[str, str] = Field(default_factory=dict)


class BM25Index:
    """In-memory BM25 baseline for deterministic course tests."""

    def __init__(self, *, k1: float = 1.2, b: float = 0.75) -> None:
        if k1 <= 0:
            raise ValueError("k1 must be > 0")
        if not 0 <= b <= 1:
            raise ValueError("b must be between 0 and 1")
        self.k1 = k1
        self.b = b
        self._chunks: dict[str, Chunk] = {}
        self._tokens: dict[str, list[str]] = {}
        self._df: Counter[str] = Counter()
        self._avgdl = 0.0

    def upsert(self, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            self._chunks[chunk.id] = chunk
        self._rebuild_statistics()

    def search(self, query: str, k: int) -> list[RankedHit]:
        if k < 1:
            raise ValueError("k must be >= 1")
        if not self._chunks:
            return []
        query_terms = tokenize(query)
        if not query_terms:
            return []

        scored: list[tuple[float, Chunk]] = []
        n_docs = len(self._chunks)
        for chunk_id, chunk in self._chunks.items():
            tokens = self._tokens[chunk_id]
            counts = Counter(tokens)
            dl = max(1, len(tokens))
            score = 0.0
            for term in query_terms:
                tf = counts.get(term, 0)
                if tf == 0:
                    continue
                df = self._df.get(term, 0)
                idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
                denom = tf + self.k1 * (1.0 - self.b + self.b * dl / max(self._avgdl, 1.0))
                score += idf * (tf * (self.k1 + 1.0) / denom)
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda item: (-item[0], item[1].id))
        return [
            RankedHit(
                id=chunk.id,
                score=score,
                rank=rank,
                retriever="bm25",
                metadata={"document_id": chunk.document_id},
            )
            for rank, (score, chunk) in enumerate(scored[:k], start=1)
        ]

    def _rebuild_statistics(self) -> None:
        self._tokens = {chunk_id: tokenize(chunk.text) for chunk_id, chunk in self._chunks.items()}
        self._df = Counter()
        for tokens in self._tokens.values():
            self._df.update(set(tokens))
        lengths = [len(tokens) for tokens in self._tokens.values()]
        self._avgdl = sum(lengths) / len(lengths) if lengths else 0.0


def reciprocal_rank_fusion(
    rankings: list[tuple[str, list[Any]]],
    *,
    rrf_k: int = 60,
    limit: int | None = None,
) -> list[HybridHit]:
    """Fuse heterogeneous ranked lists without assuming score calibration."""
    if rrf_k < 1:
        raise ValueError("rrf_k must be >= 1")
    scores: dict[str, float] = {}
    ranks: dict[str, dict[str, int]] = {}
    metadata: dict[str, dict[str, str]] = {}

    for retriever, hits in rankings:
        for fallback_rank, hit in enumerate(hits, start=1):
            hit_id = str(hit.id)
            rank = int(getattr(hit, "rank", fallback_rank))
            scores[hit_id] = scores.get(hit_id, 0.0) + 1.0 / (rrf_k + rank)
            ranks.setdefault(hit_id, {})[retriever] = rank
            raw_meta = getattr(hit, "metadata", {}) or {}
            metadata.setdefault(hit_id, {}).update(dict(raw_meta))

    fused = [
        HybridHit(id=hit_id, score=score, ranks=ranks[hit_id], metadata=metadata.get(hit_id, {}))
        for hit_id, score in scores.items()
    ]
    fused.sort(key=lambda hit: (-hit.score, hit.id))
    return fused if limit is None else fused[:limit]
