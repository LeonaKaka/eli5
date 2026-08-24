import pytest
from pydantic import ValidationError

from app.streaming import StreamCollector, StreamState
from app.structured import StructuredResult, validate_assessment


def test_cancelled_stream_keeps_partial_text_but_is_not_final() -> None:
    collector = StreamCollector()
    collector.start()
    collector.push_text("partial answer")

    result = collector.cancel()

    assert result.text == "partial answer"
    assert result.state is StreamState.CANCELLED
    assert result.is_final is False


def test_completed_stream_is_final() -> None:
    collector = StreamCollector()
    collector.start()
    collector.push_text("complete answer")

    result = collector.complete()

    assert result.state is StreamState.COMPLETED
    assert result.is_final is True


def test_structured_assessment_validates_types_and_ranges() -> None:
    result = validate_assessment(
        {
            "title": "RAG Evaluation",
            "score": 0.91,
            "tags": ["RAG", "eval"],
            "summary": "Useful benchmark paper.",
        }
    )

    assert result.score == pytest.approx(0.91)


def test_structured_assessment_rejects_valid_json_with_wrong_schema() -> None:
    with pytest.raises(ValidationError):
        validate_assessment(
            {
                "title": "RAG Evaluation",
                "score": "very high",
                "tags": "RAG",
                "summary": "Useful benchmark paper.",
            }
        )


def test_refusal_is_explicit_terminal_shape() -> None:
    result = StructuredResult(refusal="cannot complete this request")

    assert result.assessment is None
    assert result.refusal is not None
