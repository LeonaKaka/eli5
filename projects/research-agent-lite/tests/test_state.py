from app.state import AgentState


def test_state_has_isolated_messages() -> None:
    a = AgentState()
    b = AgentState()

    a.messages.append({"role": "user", "content": "hello"})

    assert len(a.messages) == 1
    assert b.messages == []
