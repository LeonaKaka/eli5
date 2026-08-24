from dataclasses import dataclass, field


@dataclass
class AgentState:
    messages: list[dict[str, str]] = field(default_factory=list)
    retry_count: int = 0
    finished: bool = False
