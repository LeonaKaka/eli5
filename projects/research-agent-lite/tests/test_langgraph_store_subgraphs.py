import pytest

from langgraph.store.memory import InMemoryStore

from app.langgraph_persistence import thread_config
from app.langgraph_store import (
    MemoryContext,
    build_store_memory_graph,
    invalidate_store_memory,
    memory_namespace,
)
from app.langgraph_subgraphs import (
    build_parent_handoff_graph,
    build_private_state_subgraph_parent,
    build_shared_state_subgraph,
)
from app.memory import MemoryKind, MemoryScope


def user_memory_request(*, memory_id: str, content: str, sensitive: bool = False):
    return {
        "id": memory_id,
        "kind": "user",
        "scope": "user",
        "content": content,
        "source": "explicit user statement",
        "confidence": 1.0,
        "reusable": True,
        "verified": True,
        "user_confirmed": True,
        "sensitive": sensitive,
        "tags": ["preference"],
    }


def test_v47_store_memory_crosses_threads_for_same_user_but_not_other_users() -> None:
    store = InMemoryStore()
    graph = build_store_memory_graph(store=store)
    user = MemoryContext(user_id="user-42")

    written = graph.invoke(
        {
            "request": user_memory_request(
                memory_id="m1",
                content="prefers concise research summaries",
            ),
            "query": "research summaries",
            "recall_scope": "user",
            "recall_kind": "user",
        },
        config=thread_config("thread-a"),
        context=user,
    )
    assert written["write_allowed"] is True
    assert written["recalled"] == ["prefers concise research summaries"]

    recalled = graph.invoke(
        {
            "request": None,
            "query": "research summaries",
            "recall_scope": "user",
            "recall_kind": "user",
        },
        config=thread_config("thread-b"),
        context=user,
    )
    assert recalled["recalled"] == ["prefers concise research summaries"]

    other = graph.invoke(
        {
            "request": None,
            "query": "research summaries",
            "recall_scope": "user",
            "recall_kind": "user",
        },
        config=thread_config("thread-c"),
        context=MemoryContext(user_id="user-99"),
    )
    assert other["recalled"] == []


def test_v47_existing_memory_policy_still_blocks_sensitive_store_writes() -> None:
    store = InMemoryStore()
    graph = build_store_memory_graph(store=store)
    context = MemoryContext(user_id="user-42")

    result = graph.invoke(
        {
            "request": user_memory_request(
                memory_id="secret-1",
                content="API key should never be ordinary memory",
                sensitive=True,
            ),
            "query": "API key",
            "recall_scope": "user",
            "recall_kind": "user",
        },
        config=thread_config("thread-sensitive"),
        context=context,
    )
    assert result["write_allowed"] is False
    namespace = memory_namespace(context, scope=MemoryScope.USER, kind=MemoryKind.USER)
    assert store.get(namespace, "secret-1") is None


def test_v47_explicit_invalidation_hides_memory_from_future_recall() -> None:
    store = InMemoryStore()
    graph = build_store_memory_graph(store=store)
    context = MemoryContext(user_id="user-42")
    config = thread_config("thread-invalidate")

    graph.invoke(
        {
            "request": user_memory_request(memory_id="m-old", content="likes old workflow"),
            "query": "old workflow",
            "recall_scope": "user",
            "recall_kind": "user",
        },
        config=config,
        context=context,
    )
    invalidate_store_memory(
        store,
        context=context,
        scope=MemoryScope.USER,
        kind=MemoryKind.USER,
        memory_id="m-old",
        reason="superseded",
    )
    result = graph.invoke(
        {
            "request": None,
            "query": "old workflow",
            "recall_scope": "user",
            "recall_kind": "user",
        },
        config=thread_config("thread-after-invalidate"),
        context=context,
    )
    assert result["recalled"] == []


def test_v47_store_adapter_rejects_silent_overwrite_of_same_memory_key() -> None:
    store = InMemoryStore()
    graph = build_store_memory_graph(store=store)
    context = MemoryContext(user_id="user-42")
    request = user_memory_request(memory_id="stable-id", content="first version")

    graph.invoke(
        {
            "request": request,
            "query": "first version",
            "recall_scope": "user",
            "recall_kind": "user",
        },
        config=thread_config("thread-write-1"),
        context=context,
    )
    with pytest.raises(ValueError, match="memory key already exists"):
        graph.invoke(
            {
                "request": {**request, "content": "silently replaced version"},
                "query": "version",
                "recall_scope": "user",
                "recall_kind": "user",
            },
            config=thread_config("thread-write-2"),
            context=context,
        )


def test_v48_shared_state_subgraph_can_be_added_directly_as_parent_node() -> None:
    graph = build_shared_state_subgraph()
    result = graph.invoke({"objective": "depinning", "evidence": "", "result": ""})

    assert "evidence-for:depinning" in result["evidence"]
    assert result["result"].startswith("answer from evidence-for:depinning")
    assert "scratch" not in result


def test_v48_private_state_subgraph_uses_wrapper_mapping_and_hides_private_notes() -> None:
    graph = build_private_state_subgraph_parent()
    result = graph.invoke({"objective": "compare methods", "specialist_result": ""})

    assert result["specialist_result"].startswith("specialist-draft:compare methods")
    assert "notes" not in result
    assert "question" not in result


def test_v48_command_parent_handoff_sends_minimal_payload_to_sibling_agent() -> None:
    graph = build_parent_handoff_graph()
    result = graph.invoke(
        {
            "objective": "domain wall disorder",
            "handoff_payload": "",
            "events": [],
            "draft": "",
        }
    )

    assert result["handoff_payload"] == "evidence:domain wall disorder"
    assert result["events"] == ["handoff:retriever→writer", "writer:done"]
    assert result["draft"] == "writer-used:evidence:domain wall disorder"
    assert "scratch" not in result
