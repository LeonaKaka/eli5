from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from .tools import ToolCall, ToolExecutor, ToolResult


class CheckpointStage(StrEnum):
    PREPARED = "prepared"
    IN_FLIGHT = "in_flight"
    COMMITTED = "committed"
    FAILED = "failed"
    COMPENSATED = "compensated"


class ReplaySafety(StrEnum):
    SAFE = "safe"
    EXTERNAL_IDEMPOTENT = "external_idempotent"
    NON_IDEMPOTENT = "non_idempotent"


class RecoveryAction(StrEnum):
    RETRY = "retry"
    REUSE_COMMITTED = "reuse_committed"
    RECONCILE = "reconcile"
    STOP = "stop"


class DurableAction(BaseModel):
    run_id: str = Field(min_length=1)
    action_id: str = Field(min_length=1)
    call: ToolCall
    replay_safety: ReplaySafety = ReplaySafety.NON_IDEMPOTENT
    idempotency_key: str | None = None

    @model_validator(mode="after")
    def validate_idempotency_contract(self) -> "DurableAction":
        if self.replay_safety is ReplaySafety.EXTERNAL_IDEMPOTENT and not self.idempotency_key:
            raise ValueError("external-idempotent actions require an idempotency_key")
        return self


class DurableCheckpoint(BaseModel):
    id: str = Field(min_length=1)
    action: DurableAction
    stage: CheckpointStage = CheckpointStage.PREPARED
    revision: int = Field(default=1, ge=1)
    result: ToolResult | None = None
    note: str | None = None


class RecoveryDecision(BaseModel):
    action: RecoveryAction
    reason: str
    checkpoint: DurableCheckpoint


class InMemoryCheckpointStore:
    """Deterministic teaching store with revision-preserving checkpoint updates."""

    def __init__(self) -> None:
        self._latest: dict[str, DurableCheckpoint] = {}
        self._history: dict[str, list[DurableCheckpoint]] = {}

    def create(self, action: DurableAction) -> DurableCheckpoint:
        checkpoint_id = f"{action.run_id}:{action.action_id}"
        if checkpoint_id in self._latest:
            raise ValueError(f"checkpoint already exists: {checkpoint_id}")
        checkpoint = DurableCheckpoint(id=checkpoint_id, action=action.model_copy(deep=True))
        self._latest[checkpoint_id] = checkpoint
        self._history[checkpoint_id] = [checkpoint]
        return checkpoint

    def get(self, checkpoint_id: str) -> DurableCheckpoint:
        checkpoint = self._latest.get(checkpoint_id)
        if checkpoint is None:
            raise KeyError(f"unknown checkpoint: {checkpoint_id}")
        return checkpoint

    def history(self, checkpoint_id: str) -> list[DurableCheckpoint]:
        if checkpoint_id not in self._history:
            raise KeyError(f"unknown checkpoint: {checkpoint_id}")
        return list(self._history[checkpoint_id])

    def update(
        self,
        checkpoint_id: str,
        *,
        stage: CheckpointStage,
        result: ToolResult | None = None,
        note: str | None = None,
    ) -> DurableCheckpoint:
        current = self.get(checkpoint_id)
        updated = current.model_copy(
            deep=True,
            update={
                "stage": stage,
                "revision": current.revision + 1,
                "result": result,
                "note": note,
            },
        )
        self._latest[checkpoint_id] = updated
        self._history[checkpoint_id].append(updated)
        return updated


class DurableActionRunner:
    """Checkpoint one tool action and make recovery policy explicit.

    This does not claim magical exactly-once execution. An IN_FLIGHT checkpoint
    means the process may have crashed after the external effect but before a
    committed result was persisted. Non-idempotent actions therefore require
    reconciliation instead of blind replay.
    """

    def __init__(self, *, executor: ToolExecutor, store: InMemoryCheckpointStore | None = None) -> None:
        self.executor = executor
        self.store = store or InMemoryCheckpointStore()

    def prepare(self, action: DurableAction) -> DurableCheckpoint:
        return self.store.create(action)

    def begin(self, checkpoint_id: str) -> DurableCheckpoint:
        checkpoint = self.store.get(checkpoint_id)
        if checkpoint.stage is not CheckpointStage.PREPARED:
            raise ValueError(f"checkpoint is not prepared: {checkpoint_id}")
        return self.store.update(checkpoint_id, stage=CheckpointStage.IN_FLIGHT)

    async def execute_prepared(self, checkpoint_id: str, *, approved: bool = False) -> DurableCheckpoint:
        checkpoint = self.begin(checkpoint_id)
        result = await self.executor.execute(checkpoint.action.call, approved=approved)
        return self.store.update(
            checkpoint_id,
            stage=CheckpointStage.COMMITTED if result.ok else CheckpointStage.FAILED,
            result=result,
        )

    def recovery_decision(self, checkpoint_id: str) -> RecoveryDecision:
        checkpoint = self.store.get(checkpoint_id)
        stage = checkpoint.stage
        if stage is CheckpointStage.COMMITTED:
            return RecoveryDecision(
                action=RecoveryAction.REUSE_COMMITTED,
                reason="a committed result is already durable; do not execute the action again",
                checkpoint=checkpoint,
            )
        if stage is CheckpointStage.PREPARED:
            return RecoveryDecision(
                action=RecoveryAction.RETRY,
                reason="execution never started, so the prepared action can be attempted",
                checkpoint=checkpoint,
            )
        if stage is CheckpointStage.IN_FLIGHT:
            if checkpoint.action.replay_safety in {
                ReplaySafety.SAFE,
                ReplaySafety.EXTERNAL_IDEMPOTENT,
            }:
                return RecoveryDecision(
                    action=RecoveryAction.RETRY,
                    reason=(
                        "the outcome is ambiguous, but the action contract says replay is safe"
                    ),
                    checkpoint=checkpoint,
                )
            return RecoveryDecision(
                action=RecoveryAction.RECONCILE,
                reason=(
                    "the action may already have produced a side effect; inspect the external system before replay"
                ),
                checkpoint=checkpoint,
            )
        if stage is CheckpointStage.FAILED:
            retryable = bool(checkpoint.result and checkpoint.result.error and checkpoint.result.error.retryable)
            return RecoveryDecision(
                action=RecoveryAction.RETRY if retryable else RecoveryAction.RECONCILE,
                reason=(
                    "the recorded failure is explicitly retryable"
                    if retryable
                    else "the failure is recorded but not safely retryable without reconciliation"
                ),
                checkpoint=checkpoint,
            )
        return RecoveryDecision(
            action=RecoveryAction.STOP,
            reason="the action is already compensated and should not be replayed automatically",
            checkpoint=checkpoint,
        )

    async def resume(self, checkpoint_id: str, *, approved: bool = False) -> DurableCheckpoint:
        decision = self.recovery_decision(checkpoint_id)
        if decision.action is RecoveryAction.REUSE_COMMITTED:
            return decision.checkpoint
        if decision.action is not RecoveryAction.RETRY:
            raise RuntimeError(f"checkpoint requires {decision.action.value}: {decision.reason}")

        current = self.store.get(checkpoint_id)
        if current.stage is CheckpointStage.IN_FLIGHT:
            self.store.update(
                checkpoint_id,
                stage=CheckpointStage.PREPARED,
                note="recovery authorized replay under the action replay-safety contract",
            )
        elif current.stage is CheckpointStage.FAILED:
            self.store.update(
                checkpoint_id,
                stage=CheckpointStage.PREPARED,
                note="recovery retry after a recorded retryable failure",
            )
        return await self.execute_prepared(checkpoint_id, approved=approved)

    def mark_compensated(self, checkpoint_id: str, *, note: str) -> DurableCheckpoint:
        checkpoint = self.store.get(checkpoint_id)
        if checkpoint.stage is not CheckpointStage.COMMITTED:
            raise ValueError("only a committed action can be marked compensated")
        if not note.strip():
            raise ValueError("compensation note is required")
        return self.store.update(
            checkpoint_id,
            stage=CheckpointStage.COMPENSATED,
            result=checkpoint.result,
            note=note,
        )
