from __future__ import annotations

import math
from collections import defaultdict

from pydantic import BaseModel, Field, field_validator


class RetrievalEvalCase(BaseModel):
    id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    relevance: dict[str, int] = Field(default_factory=dict)
    tags: set[str] = Field(default_factory=set)

    @field_validator("relevance")
    @classmethod
    def validate_relevance(cls, value: dict[str, int]) -> dict[str, int]:
        if any(score < 0 or score > 3 for score in value.values()):
            raise ValueError("relevance scores must be between 0 and 3")
        return value


class RetrievalRun(BaseModel):
    case_id: str = Field(min_length=1)
    ranked_ids: list[str] = Field(default_factory=list)


class RetrievalCaseMetrics(BaseModel):
    case_id: str
    precision_at_k: float
    recall_at_k: float
    hit_rate_at_k: float
    mrr: float
    ndcg_at_k: float


class RetrievalMetricSummary(BaseModel):
    count: int = Field(ge=0)
    precision_at_k: float
    recall_at_k: float
    hit_rate_at_k: float
    mrr: float
    ndcg_at_k: float


class RetrievalEvalReport(BaseModel):
    k: int = Field(ge=1)
    results: list[RetrievalCaseMetrics]
    overall: RetrievalMetricSummary
    by_tag: dict[str, RetrievalMetricSummary] = Field(default_factory=dict)

    @property
    def mean_precision_at_k(self) -> float:
        return self.overall.precision_at_k

    @property
    def mean_recall_at_k(self) -> float:
        return self.overall.recall_at_k

    @property
    def mean_ndcg_at_k(self) -> float:
        return self.overall.ndcg_at_k


class RetrievalEvaluator:
    def __init__(self, *, k: int = 5) -> None:
        if k < 1:
            raise ValueError("k must be >= 1")
        self.k = k

    def evaluate(
        self,
        *,
        cases: list[RetrievalEvalCase],
        runs: list[RetrievalRun],
    ) -> RetrievalEvalReport:
        if not cases:
            raise ValueError("at least one retrieval eval case is required")
        run_map = {run.case_id: run for run in runs}
        results: list[RetrievalCaseMetrics] = []
        tag_metrics: dict[str, list[RetrievalCaseMetrics]] = defaultdict(list)

        for case in cases:
            run = run_map.get(case.id, RetrievalRun(case_id=case.id, ranked_ids=[]))
            metrics = self._evaluate_case(case, run)
            results.append(metrics)
            for tag in case.tags:
                tag_metrics[tag].append(metrics)

        return RetrievalEvalReport(
            k=self.k,
            results=results,
            overall=_summarize(results),
            by_tag={tag: _summarize(items) for tag, items in sorted(tag_metrics.items())},
        )

    def _evaluate_case(
        self,
        case: RetrievalEvalCase,
        run: RetrievalRun,
    ) -> RetrievalCaseMetrics:
        positive = {doc_id for doc_id, score in case.relevance.items() if score > 0}
        top_k = run.ranked_ids[: self.k]
        relevant_in_top_k = sum(1 for doc_id in top_k if doc_id in positive)
        precision = relevant_in_top_k / self.k
        recall = relevant_in_top_k / len(positive) if positive else 1.0
        hit_rate = 1.0 if relevant_in_top_k else 0.0

        first_relevant_rank = next(
            (rank for rank, doc_id in enumerate(run.ranked_ids, start=1) if doc_id in positive),
            None,
        )
        mrr = 1.0 / first_relevant_rank if first_relevant_rank is not None else 0.0
        ndcg = ndcg_at_k(run.ranked_ids, case.relevance, self.k)

        return RetrievalCaseMetrics(
            case_id=case.id,
            precision_at_k=precision,
            recall_at_k=recall,
            hit_rate_at_k=hit_rate,
            mrr=mrr,
            ndcg_at_k=ndcg,
        )


def dcg_at_k(ranked_ids: list[str], relevance: dict[str, int], k: int) -> float:
    if k < 1:
        raise ValueError("k must be >= 1")
    score = 0.0
    for rank, doc_id in enumerate(ranked_ids[:k], start=1):
        rel = relevance.get(doc_id, 0)
        score += (2**rel - 1) / math.log2(rank + 1)
    return score


def ndcg_at_k(ranked_ids: list[str], relevance: dict[str, int], k: int) -> float:
    actual = dcg_at_k(ranked_ids, relevance, k)
    ideal_scores = sorted(relevance.values(), reverse=True)
    ideal_ids = [f"ideal:{i}" for i in range(len(ideal_scores))]
    ideal_relevance = {doc_id: score for doc_id, score in zip(ideal_ids, ideal_scores)}
    ideal = dcg_at_k(ideal_ids, ideal_relevance, k)
    return actual / ideal if ideal > 0 else 1.0


def _summarize(items: list[RetrievalCaseMetrics]) -> RetrievalMetricSummary:
    if not items:
        return RetrievalMetricSummary(
            count=0,
            precision_at_k=0.0,
            recall_at_k=0.0,
            hit_rate_at_k=0.0,
            mrr=0.0,
            ndcg_at_k=0.0,
        )
    n = len(items)
    return RetrievalMetricSummary(
        count=n,
        precision_at_k=sum(item.precision_at_k for item in items) / n,
        recall_at_k=sum(item.recall_at_k for item in items) / n,
        hit_rate_at_k=sum(item.hit_rate_at_k for item in items) / n,
        mrr=sum(item.mrr for item in items) / n,
        ndcg_at_k=sum(item.ndcg_at_k for item in items) / n,
    )
