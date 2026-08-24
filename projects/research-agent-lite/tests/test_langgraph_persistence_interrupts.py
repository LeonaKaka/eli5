from langgraph.types import Command

from app.langgraph_interrupts import (
    build_approval_graph,
    build_unsafe_pre_interrupt_graph,
)
from app.langgraph_persistence import build_persistent_graph, thread_config


def test_v45_checkpointer_persists_latest_state_and_history_per_thread() -> None:
    graph = build_persistent_graph()
    config = thread_config("thread-persist-1")

    result = graph.invoke(
        {"objective": "  compare papers  ", "stage": "new", "events": []},
        config=config,
    )
    assert result["objective"] == "compare papers"
    assert result["stage"] == "completed"
    assert result["events"] == ["normalize", "complete:compare papers"]

    latest = graph.get_state(config)
    assert latest.values["stage"] == "completed"
    assert latest.next == ()

    history = list(graph.get_state_history(config))
    assert len(history) >= 4
    assert history[0].values["stage"] == "completed"
    assert history[0].config["configurable"]["checkpoint_id"] == latest.config["configurable"]["checkpoint_id"]


def test_v45_thread_ids_isolate_checkpoint_state() -> None:
    graph = build_persistent_graph()
    a = thread_config("thread-a")
    b = thread_config("thread-b")

    graph.invoke({"objective": "paper A", "stage": "new", "events": []}, config=a)
    graph.invoke({"objective": "paper B", "stage": "new", "events": []}, config=b)

    assert graph.get_state(a).values["objective"] == "paper A"
    assert graph.get_state(b).values["objective"] == "paper B"


def test_v45_update_state_creates_a_new_checkpoint_instead_of_mutating_history() -> None:
    graph = build_persistent_graph()
    config = thread_config("thread-update")
    graph.invoke({"objective": "paper A", "stage": "new", "events": []}, config=config)

    before = graph.get_state(config)
    graph.update_state(config, {"stage": "reviewed", "events": ["manual-review"]})
    after = graph.get_state(config)

    assert after.values["stage"] == "reviewed"
    assert after.values["events"][-1] == "manual-review"
    assert before.config["configurable"]["checkpoint_id"] != after.config["configurable"]["checkpoint_id"]
    assert any(snapshot.values.get("stage") == "completed" for snapshot in graph.get_state_history(config))


def test_v46_interrupt_pauses_and_safe_resume_executes_side_effect_once() -> None:
    execution_log: list[str] = []
    graph = build_approval_graph(execution_log=execution_log)
    config = thread_config("approval-safe")

    paused = graph.invoke(
        {"action": "send report", "status": "pending", "events": []},
        config=config,
    )
    assert "__interrupt__" in paused
    assert paused["__interrupt__"][0].value["action"] == "send report"
    assert execution_log == []

    resumed = graph.invoke(Command(resume=True), config=config)
    assert resumed["status"] == "approved"
    assert resumed["events"] == ["decision:approved", "execute"]
    assert execution_log == ["send report"]


def test_v46_reject_path_resumes_without_executing_side_effect() -> None:
    execution_log: list[str] = []
    graph = build_approval_graph(execution_log=execution_log)
    config = thread_config("approval-reject")

    graph.invoke(
        {"action": "send report", "status": "pending", "events": []},
        config=config,
    )
    resumed = graph.invoke(Command(resume=False), config=config)

    assert resumed["status"] == "rejected"
    assert resumed["events"] == ["decision:rejected", "cancel"]
    assert execution_log == []


def test_v46_side_effect_before_interrupt_replays_when_node_restarts() -> None:
    execution_log: list[str] = []
    graph = build_unsafe_pre_interrupt_graph(execution_log=execution_log)
    config = thread_config("approval-unsafe")

    paused = graph.invoke(
        {"action": "charge card", "status": "pending", "events": []},
        config=config,
    )
    assert "__interrupt__" in paused
    assert execution_log == ["charge card"]

    resumed = graph.invoke(Command(resume=True), config=config)
    assert resumed["status"] == "approved"
    assert execution_log == ["charge card", "charge card"]
