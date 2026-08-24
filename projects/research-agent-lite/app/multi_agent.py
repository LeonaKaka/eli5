from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class AgentRole(StrEnum):
    SUPERVISOR = "supervisor"
    SPECIALIST = "specialist"


class HandoffKind(StrEnum):
    DELEGATE = "delegate"
    RETURN = "return"


class HandoffStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    REJECTED = "rejected"


class AgentSpec(BaseModel):
    id: str = Field(min_length=1)
    role: AgentRole
    capabilities: set[str] = Field(default_factory=set)


class HandoffContract(BaseModel):
    id: str = Field(min_length=1)
    kind: HandoffKind = HandoffKind.DELEGATE
    from_agent: str = Field(min_length=1)
    to_agent: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    required_capabilities: set[str] = Field(default_factory=set)
    context_refs: list[str] = Field(default_factory=list)
    expected_output: str = Field(min_length=1)
    return_to: str | None = None

    @model_validator(mode="after")
    def validate_contract(self) -> "HandoffContract":
        if self.from_agent == self.to_agent:
            raise ValueError("handoff cannot target the same agent")
        if self.kind is HandoffKind.DELEGATE and not self.return_to:
            raise ValueError("delegation requires an explicit return_to owner")
        return self


class HandoffRecord(BaseModel):
    contract: HandoffContract
    status: HandoffStatus = HandoffStatus.PENDING
    result_ref: str | None = None
    reason: str | None = None


class TeamState(BaseModel):
    owner_agent: str = Field(min_length=1)
    handoffs: list[HandoffRecord] = Field(default_factory=list)


class HandoffDecision(BaseModel):
    allow: bool
    reason: str
    record: HandoffRecord | None = None


class AgentDirectory:
    def __init__(self) -> None:
        self._agents: dict[str, AgentSpec] = {}

    def register(self, spec: AgentSpec) -> None:
        if spec.id in self._agents:
            raise ValueError(f"agent already registered: {spec.id}")
        self._agents[spec.id] = spec

    def get(self, agent_id: str) -> AgentSpec | None:
        return self._agents.get(agent_id)

    def candidates(self, required_capabilities: set[str]) -> list[AgentSpec]:
        return [
            spec
            for spec in self._agents.values()
            if required_capabilities.issubset(spec.capabilities)
        ]


class SupervisorRouter:
    """Pick the least-privileged capable agent deterministically."""

    def __init__(self, directory: AgentDirectory) -> None:
        self.directory = directory

    def choose(self, required_capabilities: set[str]) -> AgentSpec:
        candidates = self.directory.candidates(required_capabilities)
        if not candidates:
            raise LookupError(
                f"no agent satisfies capabilities: {sorted(required_capabilities)}"
            )
        candidates.sort(
            key=lambda spec: (
                len(spec.capabilities - required_capabilities),
                spec.role is AgentRole.SUPERVISOR,
                spec.id,
            )
        )
        return candidates[0]


class HandoffGuard:
    """Validate typed handoffs and prevent circular delegation graphs."""

    def __init__(self, *, max_delegations: int = 4) -> None:
        if max_delegations < 1:
            raise ValueError("max_delegations must be >= 1")
        self.max_delegations = max_delegations

    def evaluate(
        self,
        *,
        directory: AgentDirectory,
        state: TeamState,
        contract: HandoffContract,
    ) -> HandoffDecision:
        sender = directory.get(contract.from_agent)
        target = directory.get(contract.to_agent)
        if sender is None:
            return HandoffDecision(allow=False, reason=f"unknown sender: {contract.from_agent}")
        if target is None:
            return HandoffDecision(allow=False, reason=f"unknown target: {contract.to_agent}")
        if contract.from_agent != state.owner_agent:
            return HandoffDecision(
                allow=False,
                reason="only the current owner may delegate or return the task",
            )
        if not contract.required_capabilities.issubset(target.capabilities):
            return HandoffDecision(
                allow=False,
                reason="target agent does not satisfy the handoff capability contract",
            )

        if contract.kind is HandoffKind.RETURN:
            if contract.to_agent != contract.return_to and contract.return_to is not None:
                return HandoffDecision(
                    allow=False,
                    reason="return handoff must target the declared return owner",
                )
            return HandoffDecision(allow=True, reason="typed return is allowed")

        delegations = [
            record.contract
            for record in state.handoffs
            if record.status in {HandoffStatus.ACCEPTED, HandoffStatus.COMPLETED}
            and record.contract.kind is HandoffKind.DELEGATE
        ]
        if len(delegations) >= self.max_delegations:
            return HandoffDecision(allow=False, reason="delegation budget exhausted")

        edges = [(item.from_agent, item.to_agent) for item in delegations]
        edges.append((contract.from_agent, contract.to_agent))
        if _has_cycle(edges):
            return HandoffDecision(
                allow=False,
                reason="delegation would create a circular handoff graph",
            )
        return HandoffDecision(allow=True, reason="handoff contract is valid")


class HandoffCoordinator:
    def __init__(
        self,
        *,
        directory: AgentDirectory,
        guard: HandoffGuard | None = None,
    ) -> None:
        self.directory = directory
        self.guard = guard or HandoffGuard()

    def submit(self, state: TeamState, contract: HandoffContract) -> HandoffDecision:
        if any(record.contract.id == contract.id for record in state.handoffs):
            raise ValueError(f"handoff id already exists: {contract.id}")
        decision = self.guard.evaluate(directory=self.directory, state=state, contract=contract)
        record = HandoffRecord(
            contract=contract.model_copy(deep=True),
            status=HandoffStatus.ACCEPTED if decision.allow else HandoffStatus.REJECTED,
            reason=decision.reason,
        )
        state.handoffs.append(record)
        if decision.allow:
            state.owner_agent = contract.to_agent
        return decision.model_copy(update={"record": record})

    def complete(self, state: TeamState, handoff_id: str, *, result_ref: str) -> HandoffRecord:
        if not result_ref.strip():
            raise ValueError("result_ref is required")
        for index, record in enumerate(state.handoffs):
            if record.contract.id != handoff_id:
                continue
            if record.status is not HandoffStatus.ACCEPTED:
                raise ValueError(f"handoff is not active: {handoff_id}")
            if state.owner_agent != record.contract.to_agent:
                raise ValueError("only the current target owner can complete the handoff")
            completed = record.model_copy(
                deep=True,
                update={"status": HandoffStatus.COMPLETED, "result_ref": result_ref},
            )
            state.handoffs[index] = completed
            if record.contract.kind is HandoffKind.DELEGATE:
                state.owner_agent = record.contract.return_to or record.contract.from_agent
            else:
                state.owner_agent = record.contract.to_agent
            return completed
        raise KeyError(f"unknown handoff: {handoff_id}")


def _has_cycle(edges: list[tuple[str, str]]) -> bool:
    graph: dict[str, set[str]] = {}
    for source, target in edges:
        graph.setdefault(source, set()).add(target)
        graph.setdefault(target, set())

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for neighbor in graph[node]:
            if visit(neighbor):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph if node not in visited)
