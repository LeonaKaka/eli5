from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class FailureLayer(StrEnum):
    RETRIEVAL = "retrieval"
    EVIDENCE = "evidence"
    GENERATION = "generation"
    CITATION = "citation"


class ClaimResult(BaseModel):
    claim_id: str = Field(min_length=1)
    supported: bool
    citation_ids: list[str] = Field(default_factory=list)
    valid_citation_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_citations(self) -> "ClaimResult":
        if not set(self.valid_citation_ids).issubset(set(self.citation_ids)):
            raise ValueError("valid_citation_ids must be a subset of citation_ids")
        return self


class RAGEvalCase(BaseModel):
    id: str = Field(min_length=1)
    required_evidence_ids: set[str] = Field(default_factory=set)
    required_claim_ids: set[str] = Field(default_factory=set)
    tags: set[str] = Field(default_factory=set)


class RAGTrace(BaseModel):
    case_id: str = Field(min_length=1)
    retrieved_ids: list[str] = Field(default_factory=list)
    packed_evidence_ids: list[str] = Field(default_factory=list)
    claims: list[ClaimResult] = Field(default_factory=list)


class RAGEvalResult(BaseModel):
    case_id: str
    retrieval_coverage: float
    evidence_coverage: float
    grounded_claim_rate: float
    citation_correctness: float
    citation_completeness: float
    failure_layers: list[FailureLayer] = Field(default_factory=list)
    root_cause: FailureLayer | None = None

    @property
    def passed(self) -> bool:
        return not self.failure_layers


class RAGEvaluator:
    def evaluate(self, case: RAGEvalCase, trace: RAGTrace) -> RAGEvalResult:
        if case.id != trace.case_id:
            raise ValueError("case id and trace case_id must match")

        required_evidence = case.required_evidence_ids
        retrieved = set(trace.retrieved_ids)
        packed = set(trace.packed_evidence_ids)
        retrieval_coverage = _coverage(required_evidence, retrieved)
        evidence_coverage = _coverage(required_evidence, packed)

        claims_by_id = {claim.claim_id: claim for claim in trace.claims}
        required_claims = case.required_claim_ids
        grounded = sum(
            1 for claim_id in required_claims
            if claim_id in claims_by_id and claims_by_id[claim_id].supported
        )
        grounded_claim_rate = grounded / len(required_claims) if required_claims else 1.0

        required_claim_objects = [claims_by_id.get(claim_id) for claim_id in required_claims]
        cited_required_claims = sum(
            1 for claim in required_claim_objects if claim is not None and claim.citation_ids
        )
        citation_completeness = (
            cited_required_claims / len(required_claims) if required_claims else 1.0
        )

        all_citations = [
            citation_id
            for claim in required_claim_objects
            if claim is not None
            for citation_id in claim.citation_ids
        ]
        valid_citations = [
            citation_id
            for claim in required_claim_objects
            if claim is not None
            for citation_id in claim.valid_citation_ids
        ]
        citation_correctness = (
            len(valid_citations) / len(all_citations)
            if all_citations
            else (1.0 if not required_claims else 0.0)
        )

        failures: list[FailureLayer] = []
        if retrieval_coverage < 1.0:
            failures.append(FailureLayer.RETRIEVAL)

        retrieved_required = required_evidence & retrieved
        packed_required = required_evidence & packed
        if retrieved_required - packed_required:
            failures.append(FailureLayer.EVIDENCE)

        if grounded_claim_rate < 1.0:
            failures.append(FailureLayer.GENERATION)

        if citation_correctness < 1.0 or citation_completeness < 1.0:
            failures.append(FailureLayer.CITATION)

        root_cause = next(
            (layer for layer in (
                FailureLayer.RETRIEVAL,
                FailureLayer.EVIDENCE,
                FailureLayer.GENERATION,
                FailureLayer.CITATION,
            ) if layer in failures),
            None,
        )

        return RAGEvalResult(
            case_id=case.id,
            retrieval_coverage=retrieval_coverage,
            evidence_coverage=evidence_coverage,
            grounded_claim_rate=grounded_claim_rate,
            citation_correctness=citation_correctness,
            citation_completeness=citation_completeness,
            failure_layers=failures,
            root_cause=root_cause,
        )


def _coverage(required: set[str], observed: set[str]) -> float:
    if not required:
        return 1.0
    return len(required & observed) / len(required)
