from langchain.messages import AIMessage, HumanMessage, ToolMessage

from app.langgraph_control_flow import build_command_graph, build_send_map_reduce_graph
from app.langgraph_tools import build_tool_loop_graph


def test_v43_toolnode_executes_real_tool_call_and_loops_back_to_model() -> None:
    graph = build_tool_loop_graph()
    result = graph.invoke({"messages": [HumanMessage(content="find depinning paper")]})
    messages = result["messages"]

    assert isinstance(messages[0], HumanMessage)
    assert isinstance(messages[1], AIMessage)
    assert messages[1].tool_calls[0]["name"] == "search_papers"
    assert isinstance(messages[2], ToolMessage)
    assert "paper:depinning-baseline" in str(messages[2].content)
    assert isinstance(messages[3], AIMessage)
    assert not messages[3].tool_calls
    assert "Grounded answer from tool result" in str(messages[3].content)


def test_v43_tool_message_keeps_the_original_tool_call_id_contract() -> None:
    graph = build_tool_loop_graph()
    result = graph.invoke({"messages": [HumanMessage(content="paper A")]})
    ai_call = result["messages"][1]
    tool_result = result["messages"][2]

    assert isinstance(ai_call, AIMessage)
    assert isinstance(tool_result, ToolMessage)
    assert tool_result.tool_call_id == ai_call.tool_calls[0]["id"]


def test_v44_command_updates_state_and_routes_research_branch() -> None:
    graph = build_command_graph()
    result = graph.invoke(
        {
            "objective": "find research evidence about depinning",
            "route": None,
            "events": [],
            "answer": None,
        }
    )
    assert result["route"] == "research"
    assert result["events"] == ["decide:research", "research"]
    assert result["answer"].startswith("researched:")


def test_v44_command_can_route_direct_without_a_separate_conditional_edge() -> None:
    graph = build_command_graph()
    result = graph.invoke(
        {
            "objective": "format this title",
            "route": None,
            "events": [],
            "answer": None,
        }
    )
    assert result["route"] == "direct"
    assert result["events"] == ["decide:direct", "direct"]
    assert result["answer"] == "direct:format this title"


def test_v44_send_fans_out_dynamic_queries_and_reducer_fans_results_back_in() -> None:
    graph = build_send_map_reduce_graph()
    result = graph.invoke(
        {
            "queries": ["domain wall", "random field", "coercive field"],
            "evidence": [],
            "summary": "",
        }
    )

    assert len(result["evidence"]) == 3
    assert set(result["evidence"]) == {
        "evidence:domain wall",
        "evidence:random field",
        "evidence:coercive field",
    }
    assert result["summary"].startswith("3 evidence item(s):")
