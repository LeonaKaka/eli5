from __future__ import annotations

import heapq
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field, model_validator

from .embeddings import cosine_similarity, dot, l2_distance


class DistanceMetric(StrEnum):
    COSINE = "cosine"
    DOT = "dot"
    L2 = "l2"


class VectorRecord(BaseModel):
    id: str = Field(min_length=1)
    vector: list[float] = Field(min_length=1)
    metadata: dict[str, str] = Field(default_factory=dict)
    model_id: str = Field(min_length=1)


class SearchHit(BaseModel):
    id: str
    score: float
    metadata: dict[str, str] = Field(default_factory=dict)


class VectorIndex(Protocol):
    metric: DistanceMetric

    def upsert(self, records: list[VectorRecord]) -> None: ...

    def search(
        self,
        query: list[float],
        k: int,
        *,
        filters: dict[str, str] | None = None,
    ) -> list[SearchHit]: ...


class ExactVectorIndex:
    """Small in-memory exact baseline used for correctness and ANN recall tests."""

    def __init__(self, metric: DistanceMetric = DistanceMetric.COSINE) -> None:
        self.metric = metric
        self._records: dict[str, VectorRecord] = {}
        self._dimension: int | None = None
        self._model_id: str | None = None

    def upsert(self, records: list[VectorRecord]) -> None:
        for record in records:
            self._validate_record(record)
            self._records[record.id] = record

    def search(
        self,
        query: list[float],
        k: int,
        *,
        filters: dict[str, str] | None = None,
    ) -> list[SearchHit]:
        if k < 1:
            raise ValueError("k must be >= 1")
        self._validate_query(query)
        eligible = [r for r in self._records.values() if _matches(r, filters)]
        ranked = sorted(
            eligible,
            key=lambda record: self._score(query, record.vector),
            reverse=True,
        )
        return [
            SearchHit(id=r.id, score=self._score(query, r.vector), metadata=r.metadata)
            for r in ranked[:k]
        ]

    def _validate_record(self, record: VectorRecord) -> None:
        if self._dimension is None:
            self._dimension = len(record.vector)
            self._model_id = record.model_id
        if len(record.vector) != self._dimension:
            raise ValueError("cannot mix vector dimensions in one index")
        if record.model_id != self._model_id:
            raise ValueError("cannot mix embedding model ids in one index")

    def _validate_query(self, query: list[float]) -> None:
        if not self._records:
            return
        if self._dimension is not None and len(query) != self._dimension:
            raise ValueError("query vector dimension does not match index")

    def _score(self, query: list[float], vector: list[float]) -> float:
        if self.metric is DistanceMetric.COSINE:
            return cosine_similarity(query, vector)
        if self.metric is DistanceMetric.DOT:
            return dot(query, vector)
        return -l2_distance(query, vector)


class ApproximateGraphIndex(ExactVectorIndex):
    """Educational graph ANN, intentionally *not* a production HNSW implementation.

    Build is O(N^2): every node connects to its M nearest neighbors using exact
    distances. Query then performs a best-first graph walk and inspects at most
    candidate_budget nodes. This makes the approximation boundary observable in
    deterministic tests without pretending to reproduce HNSW's layered graph,
    insertion heuristics or performance characteristics.
    """

    def __init__(
        self,
        metric: DistanceMetric = DistanceMetric.COSINE,
        *,
        m: int = 4,
        candidate_budget: int = 16,
    ) -> None:
        super().__init__(metric)
        if m < 1:
            raise ValueError("m must be >= 1")
        if candidate_budget < 1:
            raise ValueError("candidate_budget must be >= 1")
        self.m = m
        self.candidate_budget = candidate_budget
        self._graph: dict[str, list[str]] = {}

    def upsert(self, records: list[VectorRecord]) -> None:
        super().upsert(records)
        self._rebuild_graph()

    def search(
        self,
        query: list[float],
        k: int,
        *,
        filters: dict[str, str] | None = None,
    ) -> list[SearchHit]:
        if k < 1:
            raise ValueError("k must be >= 1")
        self._validate_query(query)
        eligible = {rid for rid, r in self._records.items() if _matches(r, filters)}
        if not eligible:
            return []

        entry = min(eligible)
        frontier: list[tuple[float, str]] = [(-self._score(query, self._records[entry].vector), entry)]
        queued = {entry}
        visited: list[str] = []

        while frontier and len(visited) < self.candidate_budget:
            _, rid = heapq.heappop(frontier)
            if rid not in eligible:
                continue
            visited.append(rid)
            for neighbor in self._graph.get(rid, []):
                if neighbor not in eligible or neighbor in queued:
                    continue
                queued.add(neighbor)
                score = self._score(query, self._records[neighbor].vector)
                heapq.heappush(frontier, (-score, neighbor))

        ranked = sorted(
            (self._records[rid] for rid in visited),
            key=lambda record: self._score(query, record.vector),
            reverse=True,
        )
        return [
            SearchHit(id=r.id, score=self._score(query, r.vector), metadata=r.metadata)
            for r in ranked[:k]
        ]

    def _rebuild_graph(self) -> None:
        self._graph = {}
        records = list(self._records.values())
        for record in records:
            neighbors = [candidate for candidate in records if candidate.id != record.id]
            neighbors.sort(
                key=lambda candidate: self._score(record.vector, candidate.vector),
                reverse=True,
            )
            self._graph[record.id] = [candidate.id for candidate in neighbors[: self.m]]


def recall_at_k(exact: list[SearchHit], approximate: list[SearchHit], *, k: int) -> float:
    if k < 1:
        raise ValueError("k must be >= 1")
    truth = {hit.id for hit in exact[:k]}
    if not truth:
        return 1.0
    found = {hit.id for hit in approximate[:k]}
    return len(truth & found) / len(truth)


def _matches(record: VectorRecord, filters: dict[str, str] | None) -> bool:
    if not filters:
        return True
    return all(record.metadata.get(key) == value for key, value in filters.items())
