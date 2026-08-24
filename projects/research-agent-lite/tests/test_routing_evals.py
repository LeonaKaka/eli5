from app.evals import EvalCase, RegressionGate
from app.routing import ModelRouter, ModelSpec, NoEligibleModelError, RouteRequest


def _models() -> list[ModelSpec]:
    return [
        ModelSpec(
            name="fast",
            quality=0.62,
            cost_friendliness=0.95,
            latency_friendliness=0.95,
            reliability=0.84,
            supports_tools=True,
            supports_vision=False,
            long_context=False,
        ),
        ModelSpec(
            name="balanced",
            quality=0.82,
            cost_friendliness=0.70,
            latency_friendliness=0.74,
            reliability=0.91,
            supports_tools=True,
            supports_vision=True,
            long_context=True,
        ),
        ModelSpec(
            name="deep",
            quality=0.96,
            cost_friendliness=0.35,
            latency_friendliness=0.38,
            reliability=0.88,
            supports_tools=True,
            supports_vision=True,
            long_context=True,
        ),
    ]


def test_router_applies_capability_gate_before_ranking() -> None:
    router = ModelRouter(_models())
    decision = router.route(
        RouteRequest(
            needs_vision=True,
            quality_priority=0.1,
            cost_priority=1.0,
            latency_priority=1.0,
            reliability_priority=0.1,
        )
    )
    assert decision.model != "fast"
    assert "vision" in decision.reason


def test_router_raises_when_no_model_is_eligible() -> None:
    router = ModelRouter(
        [
            ModelSpec(
                name="text-only",
                quality=1,
                cost_friendliness=1,
                latency_friendliness=1,
                reliability=1,
                supports_vision=False,
            )
        ]
    )
    try:
        router.route(RouteRequest(needs_vision=True))
    except NoEligibleModelError:
        pass
    else:
        raise AssertionError("vision request must not silently route to a text-only model")


def test_regression_gate_blocks_critical_regression_even_if_average_improves() -> None:
    gate = RegressionGate(
        minimum_score=0.80,
        max_regression=0.05,
        critical_tags={"tool-permission"},
    )
    report = gate.evaluate(
        [
            EvalCase("qa", "quality", 0.82, 0.94),
            EvalCase("extract", "structured", 0.86, 0.95),
            EvalCase("permission", "tool-permission", 1.00, 0.96),
        ]
    )
    assert report.average_candidate > report.average_baseline
    assert not gate.accept(report)
    assert any(f.tag == "tool-permission" for f in report.failures)


def test_regression_gate_accepts_non_regressing_candidate() -> None:
    gate = RegressionGate(minimum_score=0.80, max_regression=0.03)
    report = gate.evaluate(
        [
            EvalCase("qa", "quality", 0.84, 0.90),
            EvalCase("citation", "citation", 0.88, 0.91),
        ]
    )
    assert gate.accept(report)
