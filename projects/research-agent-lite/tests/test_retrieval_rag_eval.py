from app.evals import EvalCase, RegressionGate
from app.rag_eval import (
    ClaimResult,
    FailureLayer,
    RAGEvalCase,
    RAGEvaluator,
    RAGTrace,
)
from app.retrieval_eval import (
    RetrievalEvalCase,
    RetrievalEvaluator,
    RetrievalRun,
    ndcg_at_k,
)


def test_retrieval_metrics_separate_recall_rank_and_graded_quality() -> None:
    case = RetrievalEvalCase(
        id="q1",
        query="why does disorder lower Ec",
        relevance={"d1": 3, "d2": 2, "d3": 1},
        tags={"semantic", "critical"},
    )
    run = RetrievalRun(case_id="q1", ranked_ids=["noise1", "d1", "noise2", "d2", "d3"])
    report = RetrievalEvaluator(k=3).evaluate(cases=[case], runs=[run])
    result = report.results[0]

    assert result.precision_at_k == 1 / 3
    assert result.recall_at_k == 1 / 3
    assert result.hit_rate_at_k == 1.0
    assert result.mrr == 0.5
    assert 0.0 < result.ndcg_at_k < 1.0
    assert report.by_tag["semantic"].count == 1


def test_ndcg_rewards_putting_high_relevance_items_earlier() -> None:
    relevance = {"direct": 3, "support": 2, "background": 1}
    good = ndcg_at_k(["direct", "support", "background"], relevance, 3)
    bad = ndcg_at_k(["background", "support", "direct"], relevance, 3)
    assert good == 1.0
    assert bad < good


def base_case() -> RAGEvalCase:
    return RAGEvalCase(
        id="rag1",
        required_evidence_ids={"e1"},
        required_claim_ids={"c1"},
        tags={"critical-citation"},
    )


def test_rag_eval_identifies_retrieval_as_earliest_failure() -> None:
    trace = RAGTrace(
        case_id="rag1",
        retrieved_ids=["wrong"],
        packed_evidence_ids=["wrong"],
        claims=[ClaimResult(claim_id="c1", supported=False)],
    )
    result = RAGEvaluator().evaluate(base_case(), trace)
    assert result.root_cause is FailureLayer.RETRIEVAL
    assert FailureLayer.RETRIEVAL in result.failure_layers


def test_rag_eval_identifies_evidence_packing_failure() -> None:
    trace = RAGTrace(
        case_id="rag1",
        retrieved_ids=["e1"],
        packed_evidence_ids=["other"],
        claims=[ClaimResult(claim_id="c1", supported=False)],
    )
    result = RAGEvaluator().evaluate(base_case(), trace)
    assert result.root_cause is FailureLayer.EVIDENCE
    assert result.retrieval_coverage == 1.0
    assert result.evidence_coverage == 0.0


def test_rag_eval_identifies_generation_failure_after_good_evidence() -> None:
    trace = RAGTrace(
        case_id="rag1",
        retrieved_ids=["e1"],
        packed_evidence_ids=["e1"],
        claims=[ClaimResult(claim_id="c1", supported=False, citation_ids=["e1"], valid_citation_ids=["e1"])],
    )
    result = RAGEvaluator().evaluate(base_case(), trace)
    assert result.root_cause is FailureLayer.GENERATION
    assert result.retrieval_coverage == 1.0
    assert result.evidence_coverage == 1.0
    assert result.citation_correctness == 1.0


def test_rag_eval_identifies_citation_failure_after_grounded_answer() -> None:
    trace = RAGTrace(
        case_id="rag1",
        retrieved_ids=["e1"],
        packed_evidence_ids=["e1"],
        claims=[ClaimResult(claim_id="c1", supported=True, citation_ids=["wrong"], valid_citation_ids=[])],
    )
    result = RAGEvaluator().evaluate(base_case(), trace)
    assert result.root_cause is FailureLayer.CITATION
    assert result.grounded_claim_rate == 1.0
    assert result.citation_correctness == 0.0
    assert result.citation_completeness == 1.0


def test_rag_eval_success_and_critical_regression_gate() -> None:
    trace = RAGTrace(
        case_id="rag1",
        retrieved_ids=["e1"],
        packed_evidence_ids=["e1"],
        claims=[ClaimResult(claim_id="c1", supported=True, citation_ids=["e1"], valid_citation_ids=["e1"])],
    )
    result = RAGEvaluator().evaluate(base_case(), trace)
    assert result.passed
    assert result.root_cause is None

    gate = RegressionGate(
        minimum_score=0.80,
        max_regression=0.03,
        critical_tags={"citation"},
    )
    report = gate.evaluate(
        [
            EvalCase(id="retrieval", tag="retrieval", baseline_score=0.86, candidate_score=0.92),
            EvalCase(id="citation", tag="citation", baseline_score=0.96, candidate_score=0.90),
        ]
    )
    assert not gate.accept(report)
