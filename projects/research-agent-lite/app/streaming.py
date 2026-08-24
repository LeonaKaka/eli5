from dataclasses import dataclass
from enum import StrEnum


class StreamState(StrEnum):
    PENDING = "pending"
    STREAMING = "streaming"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class StreamResult:
    text: str = ""
    state: StreamState = StreamState.PENDING
    error: str | None = None

    @property
    def is_final(self) -> bool:
        return self.state is StreamState.COMPLETED


class StreamCollector:
    """Provider-neutral collector used by UI/service adapters.

    Partial text is kept for display, but only COMPLETED is considered a final answer.
    """

    def __init__(self) -> None:
        self.result = StreamResult()

    def start(self) -> None:
        if self.result.state is not StreamState.PENDING:
            raise RuntimeError("stream already started")
        self.result.state = StreamState.STREAMING

    def push_text(self, delta: str) -> None:
        if self.result.state is not StreamState.STREAMING:
            raise RuntimeError("cannot append text to inactive stream")
        self.result.text += delta

    def complete(self) -> StreamResult:
        if self.result.state is not StreamState.STREAMING:
            raise RuntimeError("cannot complete inactive stream")
        self.result.state = StreamState.COMPLETED
        return self.result

    def cancel(self) -> StreamResult:
        if self.result.state not in {StreamState.PENDING, StreamState.STREAMING}:
            raise RuntimeError("cannot cancel terminal stream")
        self.result.state = StreamState.CANCELLED
        return self.result

    def fail(self, message: str) -> StreamResult:
        if self.result.state not in {StreamState.PENDING, StreamState.STREAMING}:
            raise RuntimeError("cannot fail terminal stream")
        self.result.state = StreamState.FAILED
        self.result.error = message
        return self.result
