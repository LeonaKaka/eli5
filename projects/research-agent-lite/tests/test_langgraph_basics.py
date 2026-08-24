from app.langgraph_basics import (
    build_bridge_graph,
    build_research_state_graph,
    initial_research_state,
)


def test_v41_bridge_graph_compiles_and_applies_partial_state_update() -> None:
    graph = build_bridge_graph()
    result = graph.invoke(
        {
            "objective": "  compare papers  ",
            "events": [],
            "step_count": 0,
        }
    )
    assert result["objective"] == "compare papers"
    assert result["events"] == ["normalize_objective"]
    assert result["step_count"] == 1


def test_v42_research_branch_accumulates_reducer_fields_across_nodes() -> None:
    graph = build_research_state_graph()
    result = graph.invoke(initial_research_state("compare paper A and paper B", mode="research"))
    assert result["route"] == "research"
    assert result["events"] == ["classify:research", "research", "synthesize"]
    assert result["evidence"] == ["evidence:compare paper A and paper B"]
    assert result["step_count"] == 3
    assert result["answer"] == "research answer with 1 evidence item(s)"


def test_v42_direct_branch_skips_research_node_but_rejoins_synthesis() -> None:
    graph = build_research_state_graph()
    result = graph.invoke(initial_research_state("say hello", mode="direct"))
    assert result["route"] == "direct"
    assert result["events"] == ["classify:direct", "direct", "synthesize"]
    assert result["evidence"] == []
    assert result["step_count"] == 3
    assert result["answer"] == "direct answer"


def test_v42_auto_router_is_deterministic_for_offline_tests() -> None:
    graph = build_research_state_graph()
    research = graph.invoke(initial_research_state("find a paper about depinning"))
    direct = graph.invoke(initial_research_state("format this title"))
    assert research["route"] == "research"
    assert direct["route"] == "direct"
