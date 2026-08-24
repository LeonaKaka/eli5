from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    name: str
    quality: float
    cost_friendliness: float
    latency_friendliness: float
    reliability: float
    supports_tools: bool = True
    supports_vision: bool = False
    long_context: bool = False


@dataclass(frozen=True)
class RouteRequest:
    needs_tools: bool = False
    needs_vision: bool = False
    needs_long_context: bool = False
    quality_priority: float = 1.0
    cost_priority: float = 0.5
    latency_priority: float = 0.5
    reliability_priority: float = 0.8


@dataclass(frozen=True)
class RouteDecision:
    model: str
    score: float
    reason: str
    fallbacks: tuple[str, ...]


class NoEligibleModelError(RuntimeError):
    pass


class ModelRouter:
    def __init__(self, models: list[ModelSpec]) -> None:
        if not models:
            raise ValueError("at least one model is required")
        self.models = list(models)

    def _eligible(self, model: ModelSpec, request: RouteRequest) -> bool:
        if request.needs_tools and not model.supports_tools:
            return False
        if request.needs_vision and not model.supports_vision:
            return False
        if request.needs_long_context and not model.long_context:
            return False
        return True

    def _score(self, model: ModelSpec, request: RouteRequest) -> float:
        weights = (
            request.quality_priority,
            request.cost_priority,
            request.latency_priority,
            request.reliability_priority,
        )
        total = sum(weights)
        if total <= 0:
            raise ValueError("routing priorities must sum to a positive value")
        values = (
            model.quality,
            model.cost_friendliness,
            model.latency_friendliness,
            model.reliability,
        )
        return sum(v * w for v, w in zip(values, weights, strict=True)) / total

    def route(self, request: RouteRequest) -> RouteDecision:
        eligible = [m for m in self.models if self._eligible(m, request)]
        if not eligible:
            raise NoEligibleModelError("no model satisfies the capability requirements")

        ranked = sorted(
            ((self._score(model, request), model) for model in eligible),
            key=lambda item: item[0],
            reverse=True,
        )
        score, winner = ranked[0]
        fallbacks = tuple(model.name for _, model in ranked[1:])
        constraints: list[str] = []
        if request.needs_tools:
            constraints.append("tools")
        if request.needs_vision:
            constraints.append("vision")
        if request.needs_long_context:
            constraints.append("long-context")
        gate = ", ".join(constraints) if constraints else "text-only"
        return RouteDecision(
            model=winner.name,
            score=score,
            reason=f"passed capability gate ({gate}) and ranked highest on configured priorities",
            fallbacks=fallbacks,
        )
