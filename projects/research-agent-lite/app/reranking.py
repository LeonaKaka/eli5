from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field

from .lexical import tokenize


class RerankCandidate(BaseModel):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    first_stage_score: float = 0.0
    first_stage_rank: int = Field(ge=1)
    metadata: dict[str, str] = Field(default_factory=dict)


class RerankHit(BaseModel):
    id: str = Field(min_length=1)
    rerank_score: float
    first_stage_score: float
    first_stage_rank: int = Field(ge=1)
    rank: int = Field(ge=1)
    metadata: dict[str, str] = Field(default_factory=dict)
    reranker_id: str = Field(min_length=1)


class Reranker(Protocol):
    reranker_id: str

    def rerank(
        self,
        *,
        query: str,
        candidates: list[RerankCandidate],
        top_n: int,
    ) -> list[RerankHit]: ...


class KeywordOverlapReranker:
    """Deterministic teaching reranker, not a production cross-encoder.

    It exists so the course can test the two-stage retrieval contract offline:
    a reranker may reorder candidates, but it can never recover a document that
    first-stage retrieval did not include.
    """

    reranker_id = "keyword-overlap-teaching-v1"

    def rerank(
        self,
        *,
        query: str,
        candidates: list[RerankCandidate],
        top_n: int,
    ) -> list[RerankHit]:
        if top_n < 1:
            raise ValueError("top_n must be >= 1")
        query_terms = set(tokenize(query))
        if not query_terms:
            scored = [(0.0, candidate) for candidate in candidates]
        else:
            scored = []
            for candidate in candidates:
                doc_terms = set(tokenize(candidate.text))
                overlap = len(query_terms & doc_terms) / len(query_terms)
                # Tiny stable tie-breaker preserves some first-stage signal without
                # pretending these heterogeneous scores are calibrated.
                score = overlap + min(max(candidate.first_stage_score, 0.0), 1.0) * 1e-4
                scored.append((score, candidate))

        scored.sort(key=lambda item: (-item[0], item[1].first_stage_rank, item[1].id))
        return [
            RerankHit(
                id=candidate.id,
                rerank_score=score,
                first_stage_score=candidate.first_stage_score,
                first_stage_rank=candidate.first_stage_rank,
                rank=rank,
                metadata=candidate.metadata,
                reranker_id=self.reranker_id,
            )
            for rank, (score, candidate) in enumerate(scored[:top_n], start=1)
        ]


class RerankService:
    def __init__(self, reranker: Reranker) -> None:
        self.reranker = reranker

    def rerank(
        self,
        *,
        query: str,
        candidates: list[RerankCandidate],
        top_n: int,
    ) -> list[RerankHit]:
        return self.reranker.rerank(query=query, candidates=candidates, top_n=top_n)
