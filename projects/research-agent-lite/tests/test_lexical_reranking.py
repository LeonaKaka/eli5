from app.chunking import Chunk
from app.lexical import BM25Index, RankedHit, reciprocal_rank_fusion
from app.multimodal import SourceRef
from app.reranking import KeywordOverlapReranker, RerankCandidate
from app.vector_index import SearchHit


def chunk(chunk_id: str, text: str, ordinal: int) -> Chunk:
    return Chunk(
        id=chunk_id,
        document_id="doc1",
        text=text,
        sources=[SourceRef(asset_id="paper1", page=ordinal + 1)],
        heading_path=["Troubleshooting"],
        ordinal=ordinal,
        policy_version="v2",
    )


def test_bm25_recovers_exact_identifier_that_generic_text_does_not_match() -> None:
    index = BM25Index()
    index.upsert(
        [
            chunk("exact", "CUDA_ERROR_700 means illegal memory access on the GPU", 0),
            chunk("generic", "GPU memory failures and debugging techniques", 1),
            chunk("other", "Driver installation and compatibility notes", 2),
        ]
    )
    hits = index.search("CUDA_ERROR_700", k=3)
    assert hits
    assert hits[0].id == "exact"


def test_rrf_rewards_document_ranked_well_by_both_retrievers() -> None:
    dense = [
        SearchHit(id="x", score=0.95),
        SearchHit(id="shared", score=0.90),
    ]
    lexical = [
        RankedHit(id="shared", score=12.0, rank=1, retriever="bm25"),
        RankedHit(id="z", score=8.0, rank=2, retriever="bm25"),
    ]
    fused = reciprocal_rank_fusion([("dense", dense), ("bm25", lexical)], rrf_k=60)
    assert fused[0].id == "shared"
    assert fused[0].ranks == {"dense": 2, "bm25": 1}


def test_reranker_can_promote_relevant_candidate_but_not_recover_missing_one() -> None:
    reranker = KeywordOverlapReranker()
    candidates = [
        RerankCandidate(
            id="generic",
            text="coercive field measurement protocol",
            first_stage_score=0.95,
            first_stage_rank=1,
        ),
        RerankCandidate(
            id="relevant",
            text="random-field disorder lowers the coercive field",
            first_stage_score=0.80,
            first_stage_rank=2,
        ),
    ]
    hits = reranker.rerank(query="disorder coercive field", candidates=candidates, top_n=2)
    assert hits[0].id == "relevant"
    assert hits[0].first_stage_rank == 2
    assert hits[0].reranker_id == reranker.reranker_id

    missing = reranker.rerank(
        query="disorder coercive field",
        candidates=[candidates[0]],
        top_n=1,
    )
    assert all(hit.id != "relevant" for hit in missing)
