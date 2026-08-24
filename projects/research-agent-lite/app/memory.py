from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from .lexical import tokenize


class MemoryKind(StrEnum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    USER = "user"


class MemoryScope(StrEnum):
    RUN = "run"
    USER = "user"
    WORKSPACE = "workspace"


class MemoryRecord(BaseModel):
    id: str = Field(min_length=1)
    kind: MemoryKind
    scope: MemoryScope
    content: str = Field(min_length=1)
    source: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    reusable: bool
    verified: bool = False
    active: bool = True
    invalidation_reason: str | None = None
    tags: set[str] = Field(default_factory=set)


class MemoryWriteRequest(BaseModel):
    id: str = Field(min_length=1)
    kind: MemoryKind
    scope: MemoryScope
    content: str = Field(min_length=1)
    source: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    reusable: bool = False
    verified: bool = False
    user_confirmed: bool = False
    sensitive: bool = False
    tags: set[str] = Field(default_factory=set)


class MemoryWriteDecision(BaseModel):
    allow: bool
    reason: str


class MemoryWriteResult(BaseModel):
    decision: MemoryWriteDecision
    record: MemoryRecord | None = None


class MemoryWritePolicy:
    """Gate persistence so every observation does not become long-term memory."""

    def __init__(self, *, minimum_confidence: float = 0.8) -> None:
        if not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be between 0 and 1")
        self.minimum_confidence = minimum_confidence

    def evaluate(self, request: MemoryWriteRequest) -> MemoryWriteDecision:
        if request.sensitive:
            return MemoryWriteDecision(
                allow=False,
                reason="sensitive information must not enter the ordinary long-term store",
            )
        if request.kind is MemoryKind.WORKING:
            return MemoryWriteDecision(
                allow=False,
                reason="working memory belongs to the current run and is not persisted here",
            )
        if request.kind is MemoryKind.USER:
            if request.scope is not MemoryScope.USER:
                return MemoryWriteDecision(
                    allow=False,
                    reason="user memory must use user scope",
                )
            if not request.user_confirmed:
                return MemoryWriteDecision(
                    allow=False,
                    reason="user memory requires an explicit/confirmed source",
                )
        if request.kind is MemoryKind.SEMANTIC and not request.verified:
            return MemoryWriteDecision(
                allow=False,
                reason="semantic memory must be verified before persistence",
            )
        if not request.reusable:
            return MemoryWriteDecision(
                allow=False,
                reason="the information has no demonstrated cross-run reuse value",
            )
        if request.confidence < self.minimum_confidence:
            return MemoryWriteDecision(
                allow=False,
                reason="confidence is below the persistence threshold",
            )
        return MemoryWriteDecision(
            allow=True,
            reason="write allowed with source, scope and confidence preserved",
        )


class MemoryStore:
    """Small in-memory store for deterministic policy and retrieval tests."""

    def __init__(self, policy: MemoryWritePolicy | None = None) -> None:
        self.policy = policy or MemoryWritePolicy()
        self._records: dict[str, MemoryRecord] = {}

    def write(self, request: MemoryWriteRequest) -> MemoryWriteResult:
        decision = self.policy.evaluate(request)
        if not decision.allow:
            return MemoryWriteResult(decision=decision)
        record = MemoryRecord(
            id=request.id,
            kind=request.kind,
            scope=request.scope,
            content=request.content,
            source=request.source,
            confidence=request.confidence,
            reusable=request.reusable,
            verified=request.verified,
            tags=request.tags,
        )
        self._records[record.id] = record
        return MemoryWriteResult(decision=decision, record=record)

    def invalidate(self, record_id: str, *, reason: str) -> MemoryRecord:
        record = self._records.get(record_id)
        if record is None:
            raise KeyError(f"unknown memory id: {record_id}")
        updated = record.model_copy(
            update={"active": False, "invalidation_reason": reason}
        )
        self._records[record_id] = updated
        return updated

    def get(self, record_id: str) -> MemoryRecord | None:
        return self._records.get(record_id)

    def search(
        self,
        query: str,
        *,
        scope: MemoryScope | None = None,
        kinds: set[MemoryKind] | None = None,
        limit: int = 5,
    ) -> list[MemoryRecord]:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        terms = set(tokenize(query))
        scored: list[tuple[int, float, str, MemoryRecord]] = []
        for record in self._records.values():
            if not record.active:
                continue
            if scope is not None and record.scope is not scope:
                continue
            if kinds is not None and record.kind not in kinds:
                continue
            overlap = len(terms & set(tokenize(record.content))) if terms else 0
            if terms and overlap == 0:
                continue
            scored.append((overlap, record.confidence, record.id, record))
        scored.sort(key=lambda item: (-item[0], -item[1], item[2]))
        return [item[3] for item in scored[:limit]]
