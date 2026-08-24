from __future__ import annotations

from mcp import Client
from mcp.server import MCPServer


PAPERS: dict[str, dict[str, str]] = {
    "rfim-domain-wall": {
        "id": "rfim-domain-wall",
        "title": "Random-field pinning of driven domain walls",
        "topic": "random field disorder depinning domain wall",
        "summary": "A compact teaching record about disorder-driven pinning and depinning.",
    },
    "sliding-ferroelectric": {
        "id": "sliding-ferroelectric",
        "title": "Sliding ferroelectric domain-wall switching",
        "topic": "sliding ferroelectric 2D domain wall switching",
        "summary": "A compact teaching record about switching dominated by domain-wall motion.",
    },
    "finite-size-scaling": {
        "id": "finite-size-scaling",
        "title": "Finite-size scaling near a depinning transition",
        "topic": "finite size scaling critical depinning",
        "summary": "A compact teaching record about collapse, critical fields and exponents.",
    },
}


mcp = MCPServer(
    "Research Assistant Capabilities",
    instructions=(
        "Provider-free teaching server. Search is read-only and deterministic. "
        "Resources expose addressed research context; prompts are reusable user-selected workflows."
    ),
)


@mcp.tool()
def search_papers(query: str, limit: int = 3) -> list[dict[str, str]]:
    """Search the teaching paper catalog by title, topic or summary."""

    normalized = query.strip().lower()
    if not normalized:
        return []
    bounded_limit = max(1, min(limit, 5))
    tokens = [token for token in normalized.split() if token]
    scored: list[tuple[int, dict[str, str]]] = []
    for paper in PAPERS.values():
        haystack = " ".join((paper["title"], paper["topic"], paper["summary"])).lower()
        score = sum(token in haystack for token in tokens)
        if score:
            scored.append((score, paper))
    scored.sort(key=lambda item: (-item[0], item[1]["id"]))
    return [dict(paper) for _, paper in scored[:bounded_limit]]


@mcp.resource("research://catalog", mime_type="application/json")
def research_catalog() -> dict[str, object]:
    """The application-readable teaching research catalog."""

    return {
        "count": len(PAPERS),
        "papers": [dict(PAPERS[key]) for key in sorted(PAPERS)],
    }


@mcp.resource("research://paper/{paper_id}", mime_type="application/json")
def research_paper(paper_id: str) -> dict[str, str]:
    """Read one addressed paper record by id."""

    if paper_id not in PAPERS:
        return {
            "id": paper_id,
            "title": "not found",
            "topic": "",
            "summary": "No teaching record exists for this paper id.",
        }
    return dict(PAPERS[paper_id])


@mcp.prompt()
def compare_papers(left_id: str, right_id: str) -> str:
    """Render a user-selected workflow for comparing two paper records."""

    return (
        "Compare the two research records selected by the user. "
        f"Read research://paper/{left_id} and research://paper/{right_id}. "
        "Contrast mechanism, evidence, assumptions, and the next experiment or simulation that would discriminate them."
    )


async def inspect_research_server() -> dict[str, object]:
    """Discover the real MCP surface in-process without a subprocess or network port."""

    async with Client(mcp) as client:
        tools = await client.list_tools()
        resources = await client.list_resources()
        templates = await client.list_resource_templates()
        prompts = await client.list_prompts()
        return {
            "protocol_version": client.protocol_version,
            "tool_names": [tool.name for tool in tools.tools],
            "resource_uris": [str(resource.uri) for resource in resources.resources],
            "resource_templates": [template.uri_template for template in templates.resource_templates],
            "prompt_names": [prompt.name for prompt in prompts.prompts],
        }


if __name__ == "__main__":
    mcp.run(transport="streamable-http", json_response=True)
