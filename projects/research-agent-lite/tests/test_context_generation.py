from app.context import ContextBuilder
from app.generation import BRAINSTORM, EXTRACT, RESEARCH, GenerationProfile


def count_words(text: str) -> int:
    return len(text.split())


def test_context_builder_keeps_high_priority_blocks_within_budget() -> None:
    builder = ContextBuilder(estimator=count_words)
    history = [
        {"role": "user", "content": "very old chat details that are not important"},
        {"role": "assistant", "content": "recent decision"},
    ]
    evidence = ["paper A key evidence", "paper B key evidence"]

    blocks = builder.build(
        instructions="follow citations",
        history=history,
        evidence=evidence,
        input_budget=12,
    )

    contents = [block.content for block in blocks]
    assert "follow citations" in contents
    assert "paper A key evidence" in contents
    assert "paper B key evidence" in contents
    assert sum(block.estimated_tokens for block in blocks) <= 12


def test_context_builder_rejects_invalid_budget() -> None:
    builder = ContextBuilder(estimator=count_words)

    try:
        builder.build(instructions="x", history=[], evidence=[], input_budget=0)
    except ValueError as exc:
        assert "input_budget" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_generation_profiles_express_task_intent() -> None:
    assert EXTRACT.randomness == "low"
    assert RESEARCH.reasoning == "high"
    assert BRAINSTORM.randomness == "high"


def test_generation_profile_rejects_invalid_output_budget() -> None:
    try:
        GenerationProfile(
            name="broken",
            randomness="low",
            reasoning="low",
            max_output_tokens=0,
        )
    except ValueError as exc:
        assert "max_output_tokens" in str(exc)
    else:
        raise AssertionError("expected ValueError")
