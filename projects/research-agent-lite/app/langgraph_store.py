from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing_extensions import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

from .memory import (
    MemoryKind,
    MemoryRecord,
    MemoryScope,
    MemoryWritePolicy,
    MemoryWriteRequest,
    _memory_terms,
)


@dataclass(frozen=True)
class MemoryContext:
    user_id: str
    workspace_id: str | None = None


class StoreMemoryState(TypedDict, total=False):
    request: dict[str, Any] | None
    query: str
    recall_scope: str
    recall_kind: str
    write_allowed: bool | None
    write_reason: str
    memory_key: str | None
    recalled: list[str]


def memory_namespace(
    context: MemoryContext,
    *,
    scope: MemoryScope,
    kind: MemoryKind,
) -> tuple[str, ...]:
    if scope is MemoryScope.USER:
        return ("user", context.user_id, "memories", kind.value)
    if scope is MemoryScope.WORKSPACE:
        if not context.workspace_id:
            raise ValueError("workspace-scoped memory requires workspace_id in runtime context")
        return ("workspace", context.workspace_id, "memories", kind.value)
    raise ValueError("run-scoped memory belongs in thread/checkpoint state, not the cross-thread Store")


def _record_value(request: MemoryWriteRequest) -> dict[str, Any]:
    record = MemoryRecord(
        id=request.id,
        kind=request.kind,
        scope=request.scope,
        content=request.content,
        source=request.source,
        confidence=request.confidence,
        reusable=request.reusable,
        verified=request.verified,
        tags=request.tags,
    )
    return record.model_dump(mode="json")


def build_store_memory_graph(
    *,
    store: BaseStore | None = None,
    policy: MemoryWritePolicy | None = None,
):
    """Compile a provider-free graph using the real LangGraph BaseStore contract.

    InMemoryStore is only the default teaching adapter. Store persistence is gated
    by the existing application MemoryWritePolicy. The checkpointer remains
    thread-scoped; the Store remains cross-thread.
    """

    memory_store: BaseStore = store if store is not None else InMemoryStore()
    write_policy = policy or MemoryWritePolicy()

    def write_memory(
        state: StoreMemoryState,
        runtime: Runtime[MemoryContext],
    ) -> dict[str, Any]:
        raw = state.get("request")
        if raw is None:
            return {
                "write_allowed": None,
                "write_reason": "no write request",
                "memory_key": None,
            }

        request = MemoryWriteRequest.model_validate(raw)
        decision = write_policy.evaluate(request)
        if not decision.allow:
            return {
                "write_allowed": False,
                "write_reason": decision.reason,
                "memory_key": None,
            }
        if request.scope is MemoryScope.RUN:
            return {
                "write_allowed": False,
                "write_reason": "run-scoped information belongs in graph thread state, not Store",
                "memory_key": None,
            }

        namespace = memory_namespace(runtime.context, scope=request.scope, kind=request.kind)
        if runtime.store is None:
            raise RuntimeError("graph was compiled without a Store")
        if runtime.store.get(namespace, request.id) is not None:
            raise ValueError(
                "memory key already exists; use a new immutable memory id or explicit invalidation"
            )

        runtime.store.put(namespace, request.id, _record_value(request))
        return {
            "write_allowed": True,
            "write_reason": decision.reason,
            "memory_key": request.id,
        }

    def recall_memory(
        state: StoreMemoryState,
        runtime: Runtime[MemoryContext],
    ) -> dict[str, list[str]]:
        if runtime.store is None:
            raise RuntimeError("graph was compiled without a Store")

        scope = MemoryScope(state.get("recall_scope", MemoryScope.USER.value))
        kind = MemoryKind(state.get("recall_kind", MemoryKind.USER.value))
        namespace = memory_namespace(runtime.context, scope=scope, kind=kind)
        query_terms = _memory_terms(state.get("query", ""))

        matches: list[tuple[str, str]] = []
        for item in runtime.store.search(namespace, limit=100):
            value = item.value
            if not value.get("active", True):
                continue
            content = str(value.get("content", ""))
            if query_terms and not (query_terms & _memory_terms(content)):
                continue
            matches.append((item.key, content))

        matches.sort(key=lambda pair: pair[0])
        return {"recalled": [content for _, content in matches]}

    builder = StateGraph(StoreMemoryState, context_schema=MemoryContext)
    builder.add_node("write_memory", write_memory)
    builder.add_node("recall_memory", recall_memory)
    builder.add_edge(START, "write_memory")
    builder.add_edge("write_memory", "recall_memory")
    builder.add_edge("recall_memory", END)
    return builder.compile(checkpointer=InMemorySaver(), store=memory_store)


def invalidate_store_memory(
    store: BaseStore,
    *,
    context: MemoryContext,
    scope: MemoryScope,
    kind: MemoryKind,
    memory_id: str,
    reason: str,
) -> None:
    """Explicitly invalidate an item instead of silently replacing its meaning."""

    namespace = memory_namespace(context, scope=scope, kind=kind)
    item = store.get(namespace, memory_id)
    if item is None:
        raise KeyError(f"unknown memory id: {memory_id}")
    value = dict(item.value)
    value["active"] = False
    value["invalidation_reason"] = reason
    store.put(namespace, memory_id, value)
