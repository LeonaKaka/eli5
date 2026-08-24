from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvalCase:
    id: str
    tag: str
    baseline_score: float
    candidate_score: float
    critical: bool = False


@dataclass(frozen=True)
class EvalFailure:
    case_id: str
    tag: str
    baseline_score: float
    candidate_score: float
    regression: float
    reason: str


@dataclass(frozen=True)
class EvalReport:
    average_baseline: float
    average_candidate: float
    failures: tuple[EvalFailure, ...]

    @property
    def delta(self) -> float:
        return self.average_candidate - self.average_baseline


class RegressionGate:
    def __init__(
        self,
        *,
        minimum_score: float,
        max_regression: float,
        critical_tags: set[str] | None = None,
    ) -> None:
        if not 0 <= minimum_score <= 1:
            raise ValueError("minimum_score must be between 0 and 1")
        if max_regression < 0:
            raise ValueError("max_regression must be non-negative")
        self.minimum_score = minimum_score
        self.max_regression = max_regression
        self.critical_tags = critical_tags or set()

    def evaluate(self, cases: list[EvalCase]) -> EvalReport:
        if not cases:
            raise ValueError("at least one eval case is required")

        failures: list[EvalFailure] = []
        baseline_total = 0.0
        candidate_total = 0.0

        for case in cases:
            baseline_total += case.baseline_score
            candidate_total += case.candidate_score
            regression = case.candidate_score - case.baseline_score
            is_critical = case.critical or case.tag in self.critical_tags

            reason: str | None = None
            if case.candidate_score < self.minimum_score:
                reason = "candidate score below minimum"
            elif regression < -self.max_regression:
                reason = "regression exceeds allowed drop"
            elif is_critical and regression < 0:
                reason = "critical slice regressed"

            if reason:
                failures.append(
                    EvalFailure(
                        case_id=case.id,
                        tag=case.tag,
                        baseline_score=case.baseline_score,
                        candidate_score=case.candidate_score,
                        regression=regression,
                        reason=reason,
                    )
                )

        n = len(cases)
        return EvalReport(
            average_baseline=baseline_total / n,
            average_candidate=candidate_total / n,
            failures=tuple(failures),
        )

    def accept(self, report: EvalReport) -> bool:
        if report.failures:
            return False
        if report.average_candidate < self.minimum_score:
            return False
        if report.delta < -self.max_regression:
            return False
        return True
