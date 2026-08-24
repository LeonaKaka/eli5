import asyncio

from pydantic import BaseModel, Field

from app.multimodal import AssetPipeline, AssetPolicy, AssetRef, MediaType
from app.tools import Permission, ToolCall, ToolExecutor, ToolRegistry, ToolSpec


class SearchArgs(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)


class EmailArgs(BaseModel):
    to: str
    body: str


def test_read_only_tool_validates_and_executes() -> None:
    registry = ToolRegistry()

    async def search_papers(query: str, top_k: int) -> dict:
        return {"query": query, "count": top_k}

    registry.register(
        ToolSpec(
            name="search_papers",
            description="Search papers",
            args_model=SearchArgs,
            permission=Permission.READ_ONLY,
        ),
        search_papers,
    )

    result = asyncio.run(
        ToolExecutor(registry).execute(
            ToolCall(
                id="call_1",
                name="search_papers",
                arguments={"query": "RAG", "top_k": 3},
            )
        )
    )

    assert result.ok is True
    assert result.call_id == "call_1"
    assert result.output == {"query": "RAG", "count": 3}


def test_invalid_tool_arguments_never_execute_handler() -> None:
    registry = ToolRegistry()
    executed = False

    def search_papers(query: str, top_k: int) -> dict:
        nonlocal executed
        executed = True
        return {}

    registry.register(
        ToolSpec("search_papers", "Search papers", SearchArgs),
        search_papers,
    )

    result = asyncio.run(
        ToolExecutor(registry).execute(
            ToolCall(
                id="call_bad",
                name="search_papers",
                arguments={"query": "RAG", "top_k": "很多"},
            )
        )
    )

    assert result.ok is False
    assert result.error is not None
    assert result.error.type == "invalid_arguments"
    assert executed is False


def test_side_effect_requires_explicit_approval() -> None:
    registry = ToolRegistry()
    sent: list[str] = []

    def send_email(to: str, body: str) -> dict:
        sent.append(to)
        return {"sent": True}

    registry.register(
        ToolSpec(
            name="send_email",
            description="Send an email",
            args_model=EmailArgs,
            permission=Permission.SIDE_EFFECT,
        ),
        send_email,
    )

    call = ToolCall(
        id="mail_1",
        name="send_email",
        arguments={"to": "person@example.com", "body": "hello"},
    )
    executor = ToolExecutor(registry)

    denied = asyncio.run(executor.execute(call))
    assert denied.ok is False
    assert denied.error is not None
    assert denied.error.type == "approval_required"
    assert sent == []

    approved = asyncio.run(executor.execute(call, approved=True))
    assert approved.ok is True
    assert sent == ["person@example.com"]


def test_pdf_asset_keeps_page_provenance() -> None:
    asset = AssetRef(
        id="paper_42",
        name="paper.pdf",
        media_type=MediaType.PDF,
        mime_type="application/pdf",
        size_bytes=18_000_000,
    )

    prepared = AssetPipeline().prepare(
        asset,
        task="compare experimental methods",
        pages=[2, 7],
    )

    assert prepared.asset_id == "paper_42"
    assert [part.source.page for part in prepared.parts] == [2, 7]
    assert all(part.source.asset_id == "paper_42" for part in prepared.parts)


def test_asset_size_policy_blocks_oversized_file() -> None:
    pipeline = AssetPipeline(AssetPolicy(max_size_bytes=1_000))
    asset = AssetRef(
        id="huge",
        name="huge.pdf",
        media_type=MediaType.PDF,
        mime_type="application/pdf",
        size_bytes=2_000,
    )

    try:
        pipeline.prepare(asset, task="summarize")
    except ValueError as exc:
        assert "size policy" in str(exc)
    else:
        raise AssertionError("oversized asset should be rejected")
