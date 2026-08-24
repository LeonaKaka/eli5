import asyncio

import pytest
from pydantic import BaseModel, ValidationError

from app.agent_control import RunStatus
from app.approval import ApprovalAction, ApprovalManager, ApprovalPolicy, ApprovalStatus
from app.orchestration import (
    ActionGraph,
    ActionNode,
    ActionStatus,
    DependencyPolicy,
    ToolOrchestrator,
)
from app.tools import Permission, ToolCall, ToolExecutor, ToolRegistry, ToolSpec


class QueryArgs(BaseModel):
    query: str


class JoinArgs(BaseModel):
    left: object | None = None
    right: object | None = None


class MessageArgs(BaseModel):
    message: str


def registry_with_tools(calls: list[str]) -> tuple[ToolRegistry, ToolExecutor]:
    registry = ToolRegistry()

    async def search_a(query: str):
        await asyncio.sleep(0)
        calls.append(f"a:{query}")
        return ["paper_a"]

    async def search_b(query: str):
        await asyncio.sleep(0)
        calls.append(f"b:{query}")
        return ["paper_b"]

    def join(left=None, right=None):
        calls.append("join")
        return {"left": left, "right": right}

    registry.register(
        ToolSpec(name="search_a", description="search source A", args_model=QueryArgs),
        search_a,
    )
    registry.register(
        ToolSpec(name="search_b", description="search source B", args_model=QueryArgs),
        search_b,
    )
    registry.register(
        ToolSpec(name="join", description="join results", args_model=JoinArgs),
        join,
    )
    return registry, ToolExecutor(registry)


def test_orchestrator_runs_independent_nodes_in_same_wave_then_joins_outputs() -> None:
    calls: list[str] = []
    _, executor = registry_with_tools(calls)
    graph = ActionGraph(
        nodes=[
            ActionNode(
                id="a",
                tool_call=ToolCall(id="ca", name="search_a", arguments={"query": "depinning"}),
            ),
            ActionNode(
                id="b",
                tool_call=ToolCall(id="cb", name="search_b", arguments={"query": "domain wall"}),
            ),
            ActionNode(
                id="join",
                dependencies=["a", "b"],
                bindings={"left": "a", "right": "b"},
                tool_call=ToolCall(id="cj", name="join", arguments={}),
            ),
        ]
    )

    result = asyncio.run(ToolOrchestrator(executor, max_concurrency=2).execute(graph))
    by_id = result.by_id()
    assert by_id["a"].wave == 1
    assert by_id["b"].wave == 1
    assert by_id["join"].wave == 2
    assert by_id["join"].output == {"left": ["paper_a"], "right": ["paper_b"]}
    assert by_id["join"].status is ActionStatus.SUCCEEDED


def test_orchestrator_all_done_join_can_keep_partial_results_after_branch_failure() -> None:
    calls: list[str] = []
    registry, executor = registry_with_tools(calls)

    def fail(query: str):
        calls.append(f"fail:{query}")
        raise RuntimeError("source unavailable")

    registry.register(
        ToolSpec(name="fail", description="failing source", args_model=QueryArgs),
        fail,
    )
    graph = ActionGraph(
        nodes=[
            ActionNode(
                id="good",
                tool_call=ToolCall(id="cg", name="search_a", arguments={"query": "q"}),
            ),
            ActionNode(
                id="bad",
                tool_call=ToolCall(id="cx", name="fail", arguments={"query": "q"}),
            ),
            ActionNode(
                id="partial_join",
                dependencies=["good", "bad"],
                dependency_policy=DependencyPolicy.ALL_DONE,
                bindings={"left": "good", "right": "bad"},
                tool_call=ToolCall(id="cp", name="join", arguments={}),
            ),
        ]
    )

    result = asyncio.run(ToolOrchestrator(executor).execute(graph)).by_id()
    assert result["bad"].status is ActionStatus.FAILED
    assert result["partial_join"].status is ActionStatus.SUCCEEDED
    assert result["partial_join"].output == {"left": ["paper_a"], "right": None}


def test_action_graph_rejects_cycles_and_invalid_bindings() -> None:
    with pytest.raises(ValidationError):
        ActionGraph(
            nodes=[
                ActionNode(
                    id="a",
                    dependencies=["b"],
                    tool_call=ToolCall(id="a", name="x", arguments={}),
                ),
                ActionNode(
                    id="b",
                    dependencies=["a"],
                    tool_call=ToolCall(id="b", name="x", arguments={}),
                ),
            ]
        )

    with pytest.raises(ValidationError):
        ActionGraph(
            nodes=[
                ActionNode(
                    id="a",
                    tool_call=ToolCall(id="a", name="x", arguments={}),
                ),
                ActionNode(
                    id="b",
                    dependencies=["a"],
                    bindings={"payload": "missing"},
                    tool_call=ToolCall(id="b", name="x", arguments={}),
                ),
            ]
        )


def approval_registry(calls: list[str]) -> tuple[ToolRegistry, ToolExecutor]:
    registry = ToolRegistry()

    def read(message: str):
        calls.append(f"read:{message}")
        return "read-ok"

    def send(message: str):
        calls.append(f"send:{message}")
        return "sent"

    def destroy(message: str):
        calls.append(f"destroy:{message}")
        return "destroyed"

    registry.register(
        ToolSpec(
            name="read_note",
            description="read",
            args_model=MessageArgs,
            permission=Permission.READ_ONLY,
        ),
        read,
    )
    registry.register(
        ToolSpec(
            name="send_message",
            description="send",
            args_model=MessageArgs,
            permission=Permission.SIDE_EFFECT,
        ),
        send,
    )
    registry.register(
        ToolSpec(
            name="destroy_data",
            description="destroy",
            args_model=MessageArgs,
            permission=Permission.DESTRUCTIVE,
        ),
        destroy,
    )
    return registry, ToolExecutor(registry)


def test_read_only_action_auto_executes_but_side_effect_waits_for_exact_approval() -> None:
    calls: list[str] = []
    registry, executor = approval_registry(calls)
    manager = ApprovalManager(registry=registry, executor=executor)

    read = asyncio.run(
        manager.submit(ToolCall(id="r1", name="read_note", arguments={"message": "paper"}))
    )
    assert read.check.action is ApprovalAction.AUTO_EXECUTE
    assert read.tool_result is not None and read.tool_result.ok
    assert calls == ["read:paper"]

    pending = asyncio.run(
        manager.submit(ToolCall(id="s1", name="send_message", arguments={"message": "hello"}))
    )
    assert pending.run_status is RunStatus.WAITING_APPROVAL
    assert pending.request is not None
    assert pending.request.status is ApprovalStatus.PENDING
    assert calls == ["read:paper"]

    resumed = asyncio.run(
        manager.resume(pending.request.id, approved=True, reviewer="human@example")
    )
    assert resumed.request is not None and resumed.request.status is ApprovalStatus.EXECUTED
    assert resumed.tool_result is not None and resumed.tool_result.ok
    assert calls == ["read:paper", "send:hello"]

    with pytest.raises(ValueError, match="already resolved"):
        asyncio.run(manager.resume(pending.request.id, approved=True, reviewer="human@example"))
    assert calls == ["read:paper", "send:hello"]


def test_human_denial_never_executes_and_destructive_is_denied_by_default() -> None:
    calls: list[str] = []
    registry, executor = approval_registry(calls)
    manager = ApprovalManager(registry=registry, executor=executor)

    pending = asyncio.run(
        manager.submit(ToolCall(id="s2", name="send_message", arguments={"message": "do not send"}))
    )
    assert pending.request is not None
    denied = asyncio.run(
        manager.resume(pending.request.id, approved=False, reviewer="human@example")
    )
    assert denied.request is not None and denied.request.status is ApprovalStatus.DENIED
    assert calls == []

    destructive = asyncio.run(
        manager.submit(ToolCall(id="d1", name="destroy_data", arguments={"message": "all"}))
    )
    assert destructive.check.action is ApprovalAction.DENY
    assert destructive.run_status is RunStatus.STOPPED
    assert calls == []


def test_policy_can_require_approval_for_destructive_action_without_auto_executing() -> None:
    calls: list[str] = []
    registry, executor = approval_registry(calls)
    manager = ApprovalManager(
        registry=registry,
        executor=executor,
        policy=ApprovalPolicy(destructive_requires_approval=True),
    )
    pending = asyncio.run(
        manager.submit(ToolCall(id="d2", name="destroy_data", arguments={"message": "scoped"}))
    )
    assert pending.check.action is ApprovalAction.REQUIRE_APPROVAL
    assert pending.run_status is RunStatus.WAITING_APPROVAL
    assert calls == []
