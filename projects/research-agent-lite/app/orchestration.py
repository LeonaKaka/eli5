from __future__ import annotations

import asyncio
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from .tools import ToolCall, ToolExecutor


class ActionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class DependencyPolicy(StrEnum):
    ALL_SUCCESS = "all_success"
    ALL_DONE = "all_done"


class ActionNode(BaseModel):
    id: str = Field(min_length=1)
    tool_call: ToolCall
    dependencies: list[str] = Field(default_factory=list)
    dependency_policy: DependencyPolicy = DependencyPolicy.ALL_SUCCESS
    # argument name -> dependency node id; the dependency output is injected
    # into that argument immediately before execution.
    bindings: dict[str, str] = Field(default_factory=dict)


class ActionGraph(BaseModel):
    nodes: list[ActionNode] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_graph(self) -> "ActionGraph":
        ids = [node.id for node in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("action node ids must be unique")
        known = set(ids)
        graph = {node.id: set(node.dependencies) for node in self.nodes}
        for node in self.nodes:
            unknown = set(node.dependencies) - known
            if unknown:
                raise ValueError(f"node {node.id} has unknown dependencies: {sorted(unknown)}")
            if node.id in node.dependencies:
                raise ValueError(f"node {node.id} cannot depend on itself")
            bad_bindings = set(node.bindings.values()) - set(node.dependencies)
            if bad_bindings:
                raise ValueError(
                    f"node {node.id} bindings must reference declared dependencies: {sorted(bad_bindings)}"
                )

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                raise ValueError("action graph contains a dependency cycle")
            if node_id in visited:
                return
            visiting.add(node_id)
            for dependency in graph[node_id]:
                visit(dependency)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in graph:
            visit(node_id)
        return self


class ActionResult(BaseModel):
    node_id: str
    status: ActionStatus
    output: Any | None = None
    error_type: str | None = None
    error_message: str | None = None
    wave: int = Field(ge=1)


class OrchestrationTraceEvent(BaseModel):
    wave: int = Field(ge=1)
    node_id: str
    event: str
    detail: str


class OrchestrationResult(BaseModel):
    results: list[ActionResult]
    trace: list[OrchestrationTraceEvent]

    def by_id(self) -> dict[str, ActionResult]:
        return {result.node_id: result for result in self.results}


class ToolOrchestrator:
    """Execute an acyclic tool graph in dependency waves.

    Nodes that are ready in the same wave can run concurrently. `ALL_SUCCESS`
    nodes are skipped when a dependency fails. `ALL_DONE` nodes may still run
    after failed dependencies, which is useful for partial-result joins.
    """

    TERMINAL = {ActionStatus.SUCCEEDED, ActionStatus.FAILED, ActionStatus.SKIPPED}

    def __init__(self, executor: ToolExecutor, *, max_concurrency: int = 4) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1")
        self.executor = executor
        self.max_concurrency = max_concurrency

    async def execute(self, graph: ActionGraph, *, approved: bool = False) -> OrchestrationResult:
        nodes = {node.id: node for node in graph.nodes}
        status = {node.id: ActionStatus.PENDING for node in graph.nodes}
        results: dict[str, ActionResult] = {}
        trace: list[OrchestrationTraceEvent] = []
        wave = 0

        while any(value is ActionStatus.PENDING for value in status.values()):
            wave += 1
            ready: list[ActionNode] = []
            progressed = False

            for node in graph.nodes:
                if status[node.id] is not ActionStatus.PENDING:
                    continue
                dependency_statuses = [status[dep] for dep in node.dependencies]
                if not all(item in self.TERMINAL for item in dependency_statuses):
                    continue

                if (
                    node.dependency_policy is DependencyPolicy.ALL_SUCCESS
                    and any(item is not ActionStatus.SUCCEEDED for item in dependency_statuses)
                ):
                    status[node.id] = ActionStatus.SKIPPED
                    results[node.id] = ActionResult(
                        node_id=node.id,
                        status=ActionStatus.SKIPPED,
                        error_type="dependency_failed",
                        error_message="a required dependency did not succeed",
                        wave=wave,
                    )
                    trace.append(
                        OrchestrationTraceEvent(
                            wave=wave,
                            node_id=node.id,
                            event="skipped",
                            detail="required dependency failed or was skipped",
                        )
                    )
                    progressed = True
                    continue
                ready.append(node)

            if ready:
                semaphore = asyncio.Semaphore(self.max_concurrency)

                async def run_node(node: ActionNode) -> ActionResult:
                    async with semaphore:
                        status[node.id] = ActionStatus.RUNNING
                        trace.append(
                            OrchestrationTraceEvent(
                                wave=wave,
                                node_id=node.id,
                                event="start",
                                detail=f"tool:{node.tool_call.name}",
                            )
                        )
                        arguments = dict(node.tool_call.arguments)
                        for argument_name, dependency_id in node.bindings.items():
                            dependency_result = results.get(dependency_id)
                            arguments[argument_name] = (
                                dependency_result.output
                                if dependency_result and dependency_result.status is ActionStatus.SUCCEEDED
                                else None
                            )
                        call = node.tool_call.model_copy(update={"arguments": arguments})
                        tool_result = await self.executor.execute(call, approved=approved)
                        action_status = ActionStatus.SUCCEEDED if tool_result.ok else ActionStatus.FAILED
                        status[node.id] = action_status
                        result = ActionResult(
                            node_id=node.id,
                            status=action_status,
                            output=tool_result.output,
                            error_type=tool_result.error.type if tool_result.error else None,
                            error_message=tool_result.error.message if tool_result.error else None,
                            wave=wave,
                        )
                        trace.append(
                            OrchestrationTraceEvent(
                                wave=wave,
                                node_id=node.id,
                                event="finish",
                                detail=("ok" if tool_result.ok else f"failed:{result.error_type}"),
                            )
                        )
                        return result

                wave_results = await asyncio.gather(*(run_node(node) for node in ready))
                for result in wave_results:
                    results[result.node_id] = result
                progressed = True

            if not progressed:
                raise RuntimeError("action graph made no progress despite passing validation")

        return OrchestrationResult(
            results=[results[node.id] for node in graph.nodes],
            trace=trace,
        )
