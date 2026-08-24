import asyncio

from pydantic import BaseModel

from app.agent_control import LoopGuard, RunBudget, RunStatus, StopReason
from app.agent_loop import AgentDecision, AgentLoop, DecisionKind, ScriptedDecisionMaker, action_fingerprint
from app.tools import Permission, ToolCall, ToolExecutor, ToolRegistry, ToolSpec


class SearchArgs(BaseModel):
    query: str


def make_executor(handler) -> ToolExecutor:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="search_papers",
            description="Search papers",
            args_model=SearchArgs,
            permission=Permission.READ_ONLY,
        ),
        handler,
    )
    return ToolExecutor(registry)


def tool_decision(call_id: str, query: str) -> AgentDecision:
    return AgentDecision(
        kind=DecisionKind.TOOL,
        tool_call=ToolCall(id=call_id, name="search_papers", arguments={"query": query}),
    )


def test_agent_loop_turns_tool_result_into_observation_then_finishes() -> None:
    calls: list[str] = []

    def search_papers(query: str):
        calls.append(query)
        return {"papers": ["paper_17"]}

    policy = ScriptedDecisionMaker(
        [
            tool_decision("c1", "depinning"),
            AgentDecision(kind=DecisionKind.FINAL, final_answer="paper_17 contains the needed evidence"),
        ]
    )
    result = asyncio.run(
        AgentLoop(
            decision_maker=policy,
            tool_executor=make_executor(search_papers),
        ).run("find evidence")
    )

    assert result.status is RunStatus.COMPLETED
    assert result.stop_reason is StopReason.FINAL_ANSWER
    assert result.final_answer == "paper_17 contains the needed evidence"
    assert result.tool_calls == 1
    assert calls == ["depinning"]
    assert result.observations[0].source == "search_papers"
    assert result.observations[0].output == {"papers": ["paper_17"]}
    assert [event.kind for event in result.trace] == ["decision", "observation", "final"]


def test_loop_guard_stops_repeated_identical_action_before_third_execution() -> None:
    calls = 0

    def search_papers(query: str):
        nonlocal calls
        calls += 1
        return {"query": query, "papers": []}

    policy = ScriptedDecisionMaker([tool_decision("c1", "rare topic")])
    result = asyncio.run(
        AgentLoop(
            decision_maker=policy,
            tool_executor=make_executor(search_papers),
            guard=LoopGuard(
                RunBudget(max_steps=8, max_tool_calls=8, max_failures=2, max_same_action=2)
            ),
        ).run("find a rare paper")
    )

    assert result.status is RunStatus.STOPPED
    assert result.stop_reason is StopReason.REPEATED_ACTION
    assert result.tool_calls == 2
    assert calls == 2


def test_loop_guard_enforces_max_steps_even_when_actions_keep_changing() -> None:
    calls: list[str] = []

    def search_papers(query: str):
        calls.append(query)
        return []

    policy = ScriptedDecisionMaker(
        [
            tool_decision("c1", "q1"),
            tool_decision("c2", "q2"),
            tool_decision("c3", "q3"),
        ]
    )
    result = asyncio.run(
        AgentLoop(
            decision_maker=policy,
            tool_executor=make_executor(search_papers),
            guard=LoopGuard(RunBudget(max_steps=2, max_tool_calls=10, max_failures=5, max_same_action=5)),
        ).run("keep searching")
    )

    assert result.stop_reason is StopReason.MAX_STEPS
    assert result.tool_calls == 2
    assert calls == ["q1", "q2"]


def test_loop_guard_stops_after_failure_budget_is_exceeded() -> None:
    calls = 0

    def search_papers(query: str):
        nonlocal calls
        calls += 1
        raise TimeoutError(f"timeout for {query}")

    policy = ScriptedDecisionMaker(
        [
            tool_decision("c1", "q1"),
            tool_decision("c2", "q2"),
            tool_decision("c3", "q3"),
        ]
    )
    result = asyncio.run(
        AgentLoop(
            decision_maker=policy,
            tool_executor=make_executor(search_papers),
            guard=LoopGuard(RunBudget(max_steps=8, max_tool_calls=8, max_failures=1, max_same_action=4)),
        ).run("search despite timeouts")
    )

    assert result.stop_reason is StopReason.FAILURE_BUDGET
    assert result.failures == 2
    assert result.tool_calls == 2
    assert calls == 2


def test_tool_budget_stops_before_executing_extra_tool() -> None:
    calls = 0

    def search_papers(query: str):
        nonlocal calls
        calls += 1
        return query

    policy = ScriptedDecisionMaker(
        [tool_decision("c1", "q1"), tool_decision("c2", "q2")]
    )
    result = asyncio.run(
        AgentLoop(
            decision_maker=policy,
            tool_executor=make_executor(search_papers),
            guard=LoopGuard(RunBudget(max_steps=5, max_tool_calls=1, max_failures=2, max_same_action=3)),
        ).run("limited calls")
    )

    assert result.stop_reason is StopReason.TOOL_BUDGET
    assert result.tool_calls == 1
    assert calls == 1


def test_action_fingerprint_is_stable_for_argument_key_order() -> None:
    a = ToolCall(id="a", name="search_papers", arguments={"query": "x", "year": 2025})
    b = ToolCall(id="b", name="search_papers", arguments={"year": 2025, "query": "x"})
    assert action_fingerprint(a) == action_fingerprint(b)
