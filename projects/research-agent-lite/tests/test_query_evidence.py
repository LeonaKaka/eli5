from app.evidence import EvidenceCandidate, EvidencePacker
from app.multimodal import SourceRef
from app.query_planning import QueryStrategy, RuleBasedTeachingQueryPlanner


def test_query_plan_preserves_original_and_decomposes_comparison() -> None:
    planner = RuleBasedTeachingQueryPlanner()
    original = "比较论文 A 和 B 的方法差异，并解释为什么 A 的 Ec 更低"
    plan = planner.plan(original)

    assert plan.original_query == original
    assert plan.strategy is QueryStrategy.DECOMPOSE
    assert plan.requires_synthesis
    assert len(plan.search_queries) == 3
    assert all(query.text != original for query in plan.search_queries)


def test_identifier_query_is_not_needlessly_rewritten() -> None:
    planner = RuleBasedTeachingQueryPlanner()
    query = "CUDA_ERROR_700"
    plan = planner.plan(query)

    assert plan.strategy is QueryStrategy.ORIGINAL
    assert plan.original_query == query
    assert [item.text for item in plan.search_queries] == [query]


def test_evidence_packer_respects_budget_source_cap_and_deduplicates() -> None:
    packer = EvidencePacker(duplicate_threshold=0.55)
    candidates = [
        EvidenceCandidate(
            id="e1",
            chunk_id="c1",
            text="random field disorder lowers coercive field Ec",
            source=SourceRef(asset_id="paperA", page=7),
            relevance_score=0.99,
            estimated_tokens=120,
        ),
        EvidenceCandidate(
            id="e2",
            chunk_id="c2",
            text="disorder lowers coercive field Ec under random field",
            source=SourceRef(asset_id="paperA", page=7),
            relevance_score=0.97,
            estimated_tokens=110,
        ),
        EvidenceCandidate(
            id="e3",
            chunk_id="c3",
            text="domain wall imaging identifies a depinning threshold",
            source=SourceRef(asset_id="paperB", page=6, region=(10, 20, 200, 240)),
            relevance_score=0.94,
            estimated_tokens=130,
        ),
        EvidenceCandidate(
            id="e4",
            chunk_id="c4",
            text="another independent result from paper A",
            source=SourceRef(asset_id="paperA", page=9),
            relevance_score=0.80,
            estimated_tokens=120,
        ),
    ]

    pack = packer.pack(candidates, budget_tokens=300, per_source_cap=1)
    assert [item.id for item in pack.items] == ["e1", "e3"]
    assert pack.total_tokens == 250
    assert pack.source_count == 2


def test_cjk_near_duplicate_evidence_is_suppressed() -> None:
    packer = EvidencePacker(duplicate_threshold=0.55)
    pack = packer.pack(
        [
            EvidenceCandidate(
                id="zh1",
                chunk_id="zh-c1",
                text="随机场无序增强会降低矫顽场并改变畴壁钉扎行为",
                source=SourceRef(asset_id="paperA", page=7),
                relevance_score=0.99,
                estimated_tokens=80,
            ),
            EvidenceCandidate(
                id="zh2",
                chunk_id="zh-c2",
                text="随机场无序增强会降低矫顽场，同时改变畴壁钉扎行为",
                source=SourceRef(asset_id="paperA", page=7),
                relevance_score=0.98,
                estimated_tokens=85,
            ),
        ],
        budget_tokens=300,
        per_source_cap=3,
    )
    assert [item.id for item in pack.items] == ["zh1"]


def test_citation_location_is_derived_from_source_ref() -> None:
    pack = EvidencePacker().pack(
        [
            EvidenceCandidate(
                id="fig3",
                chunk_id="chunk-fig3",
                text="Figure 3 shows a depinning-like threshold.",
                source=SourceRef(asset_id="paperB", page=6, region=(10, 20, 200, 240)),
                relevance_score=0.95,
                estimated_tokens=80,
            )
        ],
        budget_tokens=200,
    )

    citation = pack.citation_for("fig3")
    assert citation.asset_id == "paperB"
    assert citation.page == 6
    assert citation.region == (10, 20, 200, 240)
