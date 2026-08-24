import asyncio
from typing import Protocol

from .errors import TransientSearchError
from .models import Paper, SearchRequest


class PaperSource(Protocol):
    name: str

    async def search(self, request: SearchRequest) -> list[Paper]:
        ...


class DemoPaperSource:
    """Offline source that behaves like a small remote adapter.

    `delay` simulates I/O wait. `fail_first=True` simulates one transient
    failure so the retry path can be exercised without real network calls.
    """

    def __init__(
        self,
        name: str,
        papers: list[Paper],
        *,
        delay: float = 0.05,
        fail_first: bool = False,
    ) -> None:
        self.name = name
        self._papers = papers
        self._delay = delay
        self._fail_first = fail_first
        self._calls = 0

    async def search(self, request: SearchRequest) -> list[Paper]:
        self._calls += 1
        await asyncio.sleep(self._delay)

        if self._fail_first and self._calls == 1:
            raise TransientSearchError(f"{self.name} timed out once")

        query_words = set(request.query.lower().split())

        def relevance(paper: Paper) -> tuple[int, float]:
            title_words = set(paper.title.lower().split())
            overlap = len(query_words & title_words)
            return overlap, paper.score

        ranked = sorted(self._papers, key=relevance, reverse=True)
        return ranked[: request.top_k]
