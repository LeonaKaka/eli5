from __future__ import annotations

from collections import defaultdict, deque
from enum import StrEnum
from threading import RLock

from pydantic import BaseModel, Field

from .agent_control import RunStatus


class RunEventType(StrEnum):
    RUN_CREATED = "run_created"
    PROGRESS = "progress"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_RESOLVED = "approval_resolved"
    CANCEL_REQUESTED = "cancel_requested"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


class RunStreamEvent(BaseModel):
    """Client-safe event projection for one product Run.

    tenant_id is deliberately not part of the serialized event. Checkpoint ids,
    internal approval ids, budgets, tool payloads and raw graph state are also not
    accepted by this schema, so the SSE layer cannot accidentally dump them.
    """

    sequence: int = Field(ge=1)
    run_id: str = Field(min_length=1)
    event: RunEventType
    status: RunStatus | None = None
    phase: str | None = None
    progress: int | None = Field(default=None, ge=0, le=100)
    message: str | None = Field(default=None, max_length=500)

    def public_data(self) -> dict[str, object]:
        return self.model_dump(
            mode="json",
            exclude={"sequence", "event"},
            exclude_none=True,
        )


class InMemoryRunEventStore:
    """Bounded teaching event log used by the FastAPI SSE lesson.

    It is process-local and therefore not a production event broker. A durable,
    multi-worker deployment needs an external log/pubsub system with retention.
    """

    def __init__(self, *, max_events_per_run: int = 200) -> None:
        if max_events_per_run < 1:
            raise ValueError("max_events_per_run must be >= 1")
        self.max_events_per_run = max_events_per_run
        self._events: dict[tuple[str, str], deque[RunStreamEvent]] = defaultdict(
            lambda: deque(maxlen=self.max_events_per_run)
        )
        self._next_sequence: dict[tuple[str, str], int] = defaultdict(lambda: 1)
        self._lock = RLock()

    def append(
        self,
        *,
        tenant_id: str,
        run_id: str,
        event: RunEventType,
        status: RunStatus | None = None,
        phase: str | None = None,
        progress: int | None = None,
        message: str | None = None,
    ) -> RunStreamEvent:
        key = (tenant_id, run_id)
        with self._lock:
            sequence = self._next_sequence[key]
            self._next_sequence[key] = sequence + 1
            item = RunStreamEvent(
                sequence=sequence,
                run_id=run_id,
                event=event,
                status=status,
                phase=phase,
                progress=progress,
                message=message,
            )
            self._events[key].append(item)
            return item.model_copy(deep=True)

    def list_after(
        self,
        *,
        tenant_id: str,
        run_id: str,
        after_sequence: int = 0,
    ) -> list[RunStreamEvent]:
        if after_sequence < 0:
            raise ValueError("after_sequence must be >= 0")
        key = (tenant_id, run_id)
        with self._lock:
            return [
                item.model_copy(deep=True)
                for item in self._events.get(key, ())
                if item.sequence > after_sequence
            ]

    def oldest_sequence(self, *, tenant_id: str, run_id: str) -> int | None:
        key = (tenant_id, run_id)
        with self._lock:
            events = self._events.get(key)
            if not events:
                return None
            return events[0].sequence

    def newest_sequence(self, *, tenant_id: str, run_id: str) -> int:
        key = (tenant_id, run_id)
        with self._lock:
            return self._next_sequence[key] - 1
