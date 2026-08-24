from app.chunking import ChunkPolicy, StructureAwareChunker
from app.documents import BlockType, Document, DocumentBlock
from app.multimodal import SourceRef


def make_document() -> Document:
    return Document(
        id="doc42",
        asset_id="paper42",
        title="Depinning study",
        parser_version="layout-v1",
        blocks=[
            DocumentBlock(
                id="b0",
                kind=BlockType.HEADING,
                text="3 Domain-wall depinning",
                source=SourceRef(asset_id="paper42", page=3),
                ordinal=0,
                heading_level=1,
            ),
            DocumentBlock(
                id="b1",
                kind=BlockType.PARAGRAPH,
                text="We study field-driven domain-wall motion with quenched disorder.",
                source=SourceRef(asset_id="paper42", page=3),
                ordinal=1,
            ),
            DocumentBlock(
                id="b2",
                kind=BlockType.HEADING,
                text="3.1 Finite-size scaling",
                source=SourceRef(asset_id="paper42", page=4),
                ordinal=2,
                heading_level=2,
            ),
            DocumentBlock(
                id="b3",
                kind=BlockType.PARAGRAPH,
                text="Near depinning, the velocity follows a power law and Ec shifts with size.",
                source=SourceRef(asset_id="paper42", page=4),
                ordinal=3,
            ),
            DocumentBlock(
                id="b4",
                kind=BlockType.TABLE,
                text="Table 1: L=64,128,256; Ec=0.42,0.39,0.38",
                source=SourceRef(asset_id="paper42", page=4),
                ordinal=4,
            ),
        ],
    )


def test_document_requires_reading_order() -> None:
    blocks = list(reversed(make_document().blocks))
    try:
        Document(id="bad", asset_id="paper42", title="bad", blocks=blocks)
    except ValueError as exc:
        assert "reading order" in str(exc)
    else:
        raise AssertionError("out-of-order document should be rejected")


def test_structure_aware_chunker_preserves_heading_context_and_table() -> None:
    chunks = StructureAwareChunker().chunk(
        make_document(),
        policy=ChunkPolicy(
            target_chars=180,
            overlap_chars=0,
            preserve_tables=True,
            include_heading_path=True,
            version="v2",
        ),
    )

    assert any("3 Domain-wall depinning" in chunk.text for chunk in chunks)
    scaling = [chunk for chunk in chunks if "Finite-size scaling" in chunk.text]
    assert scaling
    assert any(chunk.sources[0].page == 4 for chunk in scaling)

    table_chunks = [chunk for chunk in chunks if "Table 1:" in chunk.text]
    assert len(table_chunks) == 1
    assert table_chunks[0].sources == [SourceRef(asset_id="paper42", page=4)]
    assert table_chunks[0].policy_version == "v2"


def test_chunk_ids_are_stable_for_same_document_and_policy() -> None:
    chunker = StructureAwareChunker()
    policy = ChunkPolicy(target_chars=180, overlap_chars=0, version="stable-v1")
    first = chunker.chunk(make_document(), policy=policy)
    second = chunker.chunk(make_document(), policy=policy)
    assert [chunk.id for chunk in first] == [chunk.id for chunk in second]
