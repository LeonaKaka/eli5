import asyncio
from collections.abc import Awaitable, Callable

from .errors import PermanentSearchError, TransientSearchError
from .models import AgentAnswer, Paper, SearchRequest
from .sources import PaperSource
from .state import AgentState

SleepFunc = Callable[[float], Awaitable[None]]


class ResearchAgent:
    def __init__(
        self,
        sources: list[PaperSource],
        *,
        max_attempts: int = 2,
        sleep_func: SleepFunc = asyncio.sleep,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")

        self.sources = sources
        self.max_attempts = max_attempts
        self.sleep_func = sleep_func
        self.state = AgentState()

    async def run(self, question: str, *, top_k: int = 5) -> AgentAnswer:
        request = SearchRequest(query=question, top_k=top_k)
        self.state.messages.append({"role": "user", "content": question})

        tasks = [self._search_source(source, request) for source in self.sources]
        source_results = await asyncio.gather(*tasks, return_exceptions=True)

        papers: list[Paper] = []
        warnings: list[str] = []

        for source, result in zip(self.sources, source_results, strict=True):
            if isinstance(result, BaseException):
                warnings.append(f"{source.name}: {type(result).__name__}: {result}")
                continue
            papers.extend(result)

        papers.sort(key=lambda paper: paper.score, reverse=True)
        selected = papers[:top_k]

        self.state.messages.append(
            {"role": "assistant", "content": f"selected {len(selected)} papers"}
        )
        self.state.finished = True

        return AgentAnswer(question=question, papers=selected, warnings=warnings)

    async def _search_source(
        self,
        source: PaperSource,
        request: SearchRequest,
    ) -> list[Paper]:
        for attempt in range(1, self.max_attempts + 1):
            try:
                return await source.search(request)
            except PermanentSearchError:
                raise
            except TransientSearchError:
                self.state.retry_count += 1
                if attempt == self.max_attempts:
                    raise
                await self.sleep_func(0.02 * (2 ** (attempt - 1)))

        raise RuntimeError("unreachable")
