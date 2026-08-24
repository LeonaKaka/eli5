import argparse
import asyncio

from .agent import ResearchAgent
from .models import Paper
from .sources import DemoPaperSource


def build_demo_agent() -> ResearchAgent:
    arxiv = DemoPaperSource(
        "arxiv",
        [
            Paper(title="RAG evaluation for scientific QA", source="arxiv", score=0.95),
            Paper(title="Agent memory and tool use", source="arxiv", score=0.82),
            Paper(title="Hybrid retrieval systems", source="arxiv", score=0.88),
        ],
        delay=0.08,
        fail_first=True,
    )

    crossref = DemoPaperSource(
        "crossref",
        [
            Paper(title="Evaluation of retrieval augmented generation", source="crossref", score=0.92),
            Paper(title="Reliable asynchronous services", source="crossref", score=0.74),
            Paper(title="Testing agentic software", source="crossref", score=0.86),
        ],
        delay=0.05,
    )

    return ResearchAgent([arxiv, crossref], max_attempts=2)


async def async_main(question: str, top_k: int) -> None:
    agent = build_demo_agent()
    answer = await agent.run(question, top_k=top_k)
    print(answer.model_dump_json(indent=2))
    print(f"\nretry_count={agent.state.retry_count}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Research Agent Lite")
    parser.add_argument("question", nargs="?", default="RAG evaluation")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    asyncio.run(async_main(args.question, args.top_k))


if __name__ == "__main__":
    main()
