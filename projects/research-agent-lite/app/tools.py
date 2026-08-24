from __future__ import annotations

import inspect
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, Field, ValidationError


class Permission(StrEnum):
    READ_ONLY = "read_only"
    SIDE_EFFECT = "side_effect"
    DESTRUCTIVE = "destructive"


class ToolCall(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolError(BaseModel):
    type: str
    message: str
    retryable: bool = False


class ToolResult(BaseModel):
    call_id: str
    ok: bool
    output: Any | None = None
    error: ToolError | None = None


ToolHandler = Callable[..., Any | Awaitable[Any]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    args_model: type[BaseModel]
    permission: Permission = Permission.READ_ONLY


@dataclass(frozen=True)
class RegisteredTool:
    spec: ToolSpec
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, spec: ToolSpec, handler: ToolHandler) -> None:
        if spec.name in self._tools:
            raise ValueError(f"tool already registered: {spec.name}")
        self._tools[spec.name] = RegisteredTool(spec=spec, handler=handler)

    def get(self, name: str) -> RegisteredTool | None:
        return self._tools.get(name)

    def specs(self) -> list[ToolSpec]:
        return [item.spec for item in self._tools.values()]


class ToolExecutor:
    """Application-side validation, permission checks, and execution.

    A model can propose a ToolCall, but only this boundary is allowed to turn
    that proposal into a real side effect.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    async def execute(self, call: ToolCall, *, approved: bool = False) -> ToolResult:
        registered = self.registry.get(call.name)
        if registered is None:
            return self._error(call.id, "unknown_tool", f"unknown tool: {call.name}")

        spec = registered.spec
        if spec.permission in {Permission.SIDE_EFFECT, Permission.DESTRUCTIVE} and not approved:
            return self._error(
                call.id,
                "approval_required",
                f"{spec.name} requires explicit approval",
            )

        try:
            args = spec.args_model.model_validate(call.arguments)
        except ValidationError as exc:
            return self._error(call.id, "invalid_arguments", str(exc))

        try:
            value = registered.handler(**args.model_dump())
            if inspect.isawaitable(value):
                value = await value
        except TimeoutError as exc:
            return self._error(call.id, "timeout", str(exc) or "tool timed out", retryable=True)
        except Exception as exc:  # normalize internal failures at this boundary
            return self._error(call.id, "tool_failed", str(exc))

        return ToolResult(call_id=call.id, ok=True, output=value)

    @staticmethod
    def _error(call_id: str, kind: str, message: str, *, retryable: bool = False) -> ToolResult:
        return ToolResult(
            call_id=call_id,
            ok=False,
            error=ToolError(type=kind, message=message, retryable=retryable),
        )
