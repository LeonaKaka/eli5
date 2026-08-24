from app.chunking import Chunk
from app.embeddings import (
    DeterministicToyEmbeddingProvider,
    EmbeddingService,
    cosine_similarity,
)
from app.multimodal import SourceRef
from app.vector_index import (
    ApproximateGraphIndex,
    DistanceMetric,
    ExactVectorIndex,
    VectorRecord,
    recall_at_k,
)


def make_chunks() -> list[Chunk]:
    return [
        Chunk(
            id="c1",
            document_id="doc1",
            text="Domain-wall depinning under random-field disorder",
            sources=[SourceRef(asset_id="paper1", page=3)],
            heading_path=["Results"],
            ordinal=0,
            policy_version="v2",
        ),
        Chunk(
            id="c2",
            document_id="doc1",
            text="Finite-size scaling of coercive field Ec",
            sources=[SourceRef(asset_id="paper1", page=4)],
            heading_path=["Results", "Scaling"],
            ordinal=1,
            policy_version="v2",
        ),
    ]


def test_embedding_service_records_model_dimension_and_normalization() -> None:
    provider = DeterministicToyEmbeddingProvider(dimension=12)
    records = EmbeddingService(provider).embed_chunks(make_chunks())
    assert len(records) == 2
    assert all(record.model_id == provider.model_id for record in records)
    assert all(record.dimension == 12 for record in records)
    assert all(record.normalized for record in records)
    assert all(len(record.vector) == 12 for record in records)
    assert cosine_similarity(records[0].vector, records[0].vector) > 0.999


def test_exact_index_rejects_mixed_embedding_spaces_and_honors_filters() -> None:
    index = ExactVectorIndex(metric=DistanceMetric.L2)
    index.upsert(
        [
            VectorRecord(id="a", vector=[0.0, 0.0], metadata={"tenant": "A"}, model_id="m1"),
            VectorRecord(id="b", vector=[1.0, 0.0], metadata={"tenant": "B"}, model_id="m1"),
        ]
    )
    hits = index.search([0.9, 0.0], k=2, filters={"tenant": "A"})
    assert [hit.id for hit in hits] == ["a"]

    try:
        index.upsert([VectorRecord(id="bad", vector=[0.0, 0.0], model_id="m2")])
    except ValueError as exc:
        assert "model ids" in str(exc)
    else:
        raise AssertionError("mixing embedding model ids should be rejected")


def test_approximate_graph_search_exposes_candidate_budget_recall_tradeoff() -> None:
    records = [
        VectorRecord(id=f"v{i}", vector=[float(i), 0.0], model_id="line-v1")
        for i in range(6)
    ]
    query = [4.1, 0.0]

    exact = ExactVectorIndex(metric=DistanceMetric.L2)
    exact.upsert(records)
    truth = exact.search(query, k=1)
    assert truth[0].id == "v4"

    low_budget = ApproximateGraphIndex(
        metric=DistanceMetric.L2,
        m=2,
        candidate_budget=2,
    )
    low_budget.upsert(records)
    low = low_budget.search(query, k=1)

    high_budget = ApproximateGraphIndex(
        metric=DistanceMetric.L2,
        m=2,
        candidate_budget=6,
    )
    high_budget.upsert(records)
    high = high_budget.search(query, k=1)

    assert recall_at_k(truth, low, k=1) <= recall_at_k(truth, high, k=1)
    assert high[0].id == "v4"
