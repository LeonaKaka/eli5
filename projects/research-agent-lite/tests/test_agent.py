import asyncio

from app.agent import ResearchAgent
from app.errors import PermanentSearchError, TransientSearchError
from app.models import Paper, SearchRequest


async def no_sleep(_: float) -> None:
    return None


class StaticSource:
    def __init__(self, name: str, papers: list[Paper]) -> None:
        self.name = name
        self.papers = papers

    async def search(self, request: SearchRequest) -> list[Paper]:
        return self.papers[: request.top_k]


class FlakySource:
    name = "flaky"

    def __init__(self) -> None:
        self.calls = 0

    async def search(self, request: SearchRequest) -> list[Paper]:
        self.calls += 1
        if self.calls == 1:
            raise TransientSearchError("temporary timeout")
        return [Paper(title="Recovered paper", source=self.name, score=0.91)]


class BrokenSource:
    name = "broken"

    async def search(self, request: SearchRequest) -> list[Paper]:
        raise PermanentSearchError("bad credentials")


def test_agent_merges_and_ranks_sources() -> None:
    async def scenario() -> None:
        a = StaticSource("a", [Paper(title="A", source="a", score=0.70)])
        b = StaticSource("b", [Paper(title="B", source="b", score=0.95)])
        agent = ResearchAgent([a, b], sleep_func=no_sleep)
        answer = await agent.run("RAG", top_k=2)
        assert [paper.title for paper in answer.papers] == ["B", "A"]
        assert answer.warnings == []
        assert agent.state.finished is True

    asyncio.run(scenario())


def test_transient_failure_is_retried() -> None:
    async def scenario() -> None:
        source = FlakySource()
        agent = ResearchAgent([source], max_attempts=2, sleep_func=no_sleep)
        answer = await agent.run("RAG")
        assert source.calls == 2
        assert agent.state.retry_count == 1
        assert answer.papers[0].title == "Recovered paper"

    asyncio.run(scenario())


def test_permanent_failure_becomes_partial_result_warning() -> None:
    async def scenario() -> None:
        healthy = StaticSource(
            "healthy",
            [Paper(title="Useful result", source="healthy", score=0.88)],
        )
        broken = BrokenSource()
        agent = ResearchAgent([healthy, broken], sleep_func=no_sleep)
        answer = await agent.run("RAG")
        assert [paper.title for paper in answer.papers] == ["Useful result"]
        assert len(answer.warnings) == 1
        assert "PermanentSearchError" in answer.warnings[0]

    asyncio.run(scenario())
