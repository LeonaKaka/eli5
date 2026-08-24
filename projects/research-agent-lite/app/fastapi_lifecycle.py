from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI
from pydantic import BaseModel


class HealthCheck(BaseModel):
    name: str
    required: bool
    ready: bool


class HealthResponse(BaseModel):
    status: str
    checks: list[HealthCheck] = []


@dataclass
class ManagedDependency:
    """Small teaching lifecycle adapter for one long-lived process resource.

    Real implementations would own a DB pool, HTTP client, queue connection,
    checkpointer client, etc. The contract deliberately separates lifecycle from
    per-request dependency injection.
    """

    name: str
    required: bool = True
    ready_on_start: bool = True
    fail_on_start: bool = False
    started: bool = False
    ready: bool = False
    closed: bool = False

    async def start(self) -> None:
        if self.fail_on_start:
            raise RuntimeError(f"failed to start dependency: {self.name}")
        self.started = True
        self.closed = False
        self.ready = self.ready_on_start

    async def close(self) -> None:
        self.ready = False
        self.started = False
        self.closed = True


class RuntimeResourceManager:
    """Own process-scoped resources and expose liveness/readiness state.

    Liveness intentionally does not probe external dependencies. Readiness does:
    a process can be alive while it should be removed from production traffic.
    """

    def __init__(self, dependencies: list[ManagedDependency] | None = None) -> None:
        deps = dependencies or [
            ManagedDependency("run_store"),
            ManagedDependency("job_queue"),
            ManagedDependency("graph_runtime"),
            ManagedDependency("event_stream"),
        ]
        if len({dep.name for dep in deps}) != len(deps):
            raise ValueError("dependency names must be unique")
        self._deps = {dep.name: dep for dep in deps}
        self.started = False
        self.closed = False

    @property
    def dependencies(self) -> tuple[ManagedDependency, ...]:
        return tuple(self._deps.values())

    async def start(self) -> None:
        started: list[ManagedDependency] = []
        try:
            for dependency in self._deps.values():
                await dependency.start()
                started.append(dependency)
        except Exception:
            for dependency in reversed(started):
                await dependency.close()
            self.started = False
            self.closed = True
            raise
        self.started = True
        self.closed = False

    async def close(self) -> None:
        for dependency in reversed(tuple(self._deps.values())):
            if dependency.started or not dependency.closed:
                await dependency.close()
        self.started = False
        self.closed = True

    def set_ready(self, name: str, ready: bool) -> None:
        dependency = self._deps.get(name)
        if dependency is None:
            raise KeyError(name)
        if not dependency.started:
            raise RuntimeError(f"dependency has not started: {name}")
        dependency.ready = ready

    def live(self) -> HealthResponse:
        # If this endpoint can execute, the process/event loop is alive enough to
        # answer. External dependency failures must not turn liveness red.
        return HealthResponse(status="live", checks=[])

    def readiness(self) -> HealthResponse:
        checks = [
            HealthCheck(name=dep.name, required=dep.required, ready=dep.ready)
            for dep in self._deps.values()
        ]
        ready = self.started and all(check.ready for check in checks if check.required)
        return HealthResponse(status="ready" if ready else "not_ready", checks=checks)

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        app.state.resource_manager = self
        await self.start()
        try:
            yield
        finally:
            await self.close()
