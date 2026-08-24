from __future__ import annotations

from pydantic import BaseModel, Field

from .lexical import tokenize
from .multimodal import SourceRef


class EvidenceCandidate(BaseModel):
    id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source: SourceRef
    relevance_score: float
    estimated_tokens: int = Field(gt=0)


class CitationRef(BaseModel):
    evidence_id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    page: int | None = Field(default=None, ge=1)
    timestamp_ms: int | None = Field(default=None, ge=0)
    region: tuple[int, int, int, int] | None = None

    @classmethod
    def from_evidence(cls, item: "EvidenceItem") -> "CitationRef":
        return cls(
            evidence_id=item.id,
            asset_id=item.source.asset_id,
            page=item.source.page,
            timestamp_ms=item.source.timestamp_ms,
            region=item.source.region,
        )


class EvidenceItem(BaseModel):
    id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source: SourceRef
    relevance_score: float
    estimated_tokens: int = Field(gt=0)


class EvidencePack(BaseModel):
    items: list[EvidenceItem]
    total_tokens: int = Field(ge=0)
    budget_tokens: int = Field(gt=0)
    source_count: int = Field(ge=0)
    packer_version: str = Field(min_length=1)

    def citation_for(self, evidence_id: str) -> CitationRef:
        for item in self.items:
            if item.id == evidence_id:
                return CitationRef.from_evidence(item)
        raise KeyError(f"unknown evidence id: {evidence_id}")


class EvidencePacker:
    """Greedy teaching evidence packer with budget, dedup and source caps.

    The implementation is intentionally simple and deterministic. Production
    systems may use learned diversity/MMR or claim-aware packing, but the core
    contract remains: keep provenance attached and never invent citation
    locations after generation.
    """

    packer_version = "evidence-greedy-v1"

    def __init__(self, *, duplicate_threshold: float = 0.72) -> None:
        if not 0.0 <= duplicate_threshold <= 1.0:
            raise ValueError("duplicate_threshold must be between 0 and 1")
        self.duplicate_threshold = duplicate_threshold

    def pack(
        self,
        candidates: list[EvidenceCandidate],
        *,
        budget_tokens: int,
        per_source_cap: int = 3,
    ) -> EvidencePack:
        if budget_tokens < 1:
            raise ValueError("budget_tokens must be >= 1")
        if per_source_cap < 1:
            raise ValueError("per_source_cap must be >= 1")

        selected: list[EvidenceItem] = []
        by_source: dict[str, int] = {}
        used = 0

        for candidate in sorted(candidates, key=lambda x: (-x.relevance_score, x.id)):
            source_key = candidate.source.asset_id
            if by_source.get(source_key, 0) >= per_source_cap:
                continue
            if used + candidate.estimated_tokens > budget_tokens:
                continue
            if any(self._is_near_duplicate(candidate.text, item.text) for item in selected):
                continue

            item = EvidenceItem(**candidate.model_dump())
            selected.append(item)
            used += item.estimated_tokens
            by_source[source_key] = by_source.get(source_key, 0) + 1

        return EvidencePack(
            items=selected,
            total_tokens=used,
            budget_tokens=budget_tokens,
            source_count=len(by_source),
            packer_version=self.packer_version,
        )

    def _is_near_duplicate(self, left: str, right: str) -> bool:
        a = self._terms(left)
        b = self._terms(right)
        if not a or not b:
            return False
        return len(a & b) / len(a | b) >= self.duplicate_threshold

    @staticmethod
    def _terms(text: str) -> set[str]:
        terms: set[str] = set()
        for token in tokenize(text):
            has_cjk = any("\u4e00" <= ch <= "\u9fff" for ch in token)
            if has_cjk and len(token) > 1:
                terms.update(token[i : i + 2] for i in range(len(token) - 1))
            else:
                terms.add(token)
        return terms
