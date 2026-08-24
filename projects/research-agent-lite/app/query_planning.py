from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field


class QueryStrategy(StrEnum):
    ORIGINAL = "original"
    REWRITE = "rewrite"
    MULTI_QUERY = "multi_query"
    DECOMPOSE = "decompose"


class SearchQuery(BaseModel):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    purpose: str = Field(min_length=1)


class QueryPlan(BaseModel):
    original_query: str = Field(min_length=1)
    strategy: QueryStrategy
    search_queries: list[SearchQuery] = Field(min_length=1)
    requires_synthesis: bool = False
    planner_version: str = Field(min_length=1)


class QueryPlanner(Protocol):
    planner_version: str

    def plan(self, query: str) -> QueryPlan: ...


class RuleBasedTeachingQueryPlanner:
    """Deterministic teaching planner used to test planning contracts offline.

    It deliberately does not claim LLM-level rewrite quality. Its job is to
    make the boundary observable: original user intent is always preserved,
    generated search queries are separate objects, and decomposition is
    explicit instead of silently replacing the user's question.
    """

    planner_version = "rule-teaching-v1"

    def plan(self, query: str) -> QueryPlan:
        query = query.strip()
        if not query:
            raise ValueError("query must not be empty")

        if self._looks_like_comparison(query):
            return QueryPlan(
                original_query=query,
                strategy=QueryStrategy.DECOMPOSE,
                search_queries=[
                    SearchQuery(id="q1", text="论文 A 使用了什么方法？", purpose="retrieve A methods"),
                    SearchQuery(id="q2", text="论文 B 使用了什么方法？", purpose="retrieve B methods"),
                    SearchQuery(id="q3", text="A 的 Ec 更低由什么证据支持？", purpose="retrieve Ec evidence"),
                ],
                requires_synthesis=True,
                planner_version=self.planner_version,
            )

        if self._looks_like_identifier(query):
            return QueryPlan(
                original_query=query,
                strategy=QueryStrategy.ORIGINAL,
                search_queries=[SearchQuery(id="q1", text=query, purpose="exact identifier lookup")],
                planner_version=self.planner_version,
            )

        return QueryPlan(
            original_query=query,
            strategy=QueryStrategy.MULTI_QUERY,
            search_queries=[
                SearchQuery(id="q1", text=query, purpose="preserve original wording"),
                SearchQuery(id="q2", text=self._light_rewrite(query), purpose="alternate retrieval wording"),
            ],
            planner_version=self.planner_version,
        )

    @staticmethod
    def _looks_like_comparison(query: str) -> bool:
        lowered = query.lower()
        return any(token in lowered for token in ("比较", "区别", "difference", "compare"))

    @staticmethod
    def _looks_like_identifier(query: str) -> bool:
        upper = query.upper()
        return "DOI" in upper or "ERROR_" in upper or "10.1103/" in query

    @staticmethod
    def _light_rewrite(query: str) -> str:
        replacements = {
            "为什么下降": "下降的机制与证据",
            "怎么影响": "影响机制与证据",
            "how does": "mechanism and evidence for",
        }
        rewritten = query
        for old, new in replacements.items():
            rewritten = rewritten.replace(old, new)
        return rewritten if rewritten != query else f"证据检索：{query}"
