from __future__ import annotations

from collections import Counter, defaultdict
from enum import StrEnum
from statistics import mean

from pydantic import BaseModel, Field, model_validator


class SpanLayer(StrEnum):
    AGENT = "agent"
    MODEL = "model"
    RETRIEVAL = "retrieval"
    TOOL = "tool"
    RUNTIME = "runtime"
    RETRY = "retry"
    HANDOFF = "handoff"


class SpanStatus(StrEnum):
    OK = "ok"
    ERROR = "error"


class RunSpan(BaseModel):
    """One operational span in a Run trace.

    The course intentionally records compact attributes instead of raw prompts,
    documents or tool payloads. Production tracing should treat full model/tool
    content as opt-in sensitive telemetry rather than a default debugging dump.
    """

    name: str = Field(min_length=1)
    layer: SpanLayer
    duration_ms: float = Field(ge=0)
    status: SpanStatus = SpanStatus.OK
    error_type: str | None = None
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0)
    attributes: dict[str, str | int | float | bool] = Field(default_factory=dict)

    @model_validator(mode="after")
    def error_span_needs_type(self) -> "RunSpan":
        if self.status is SpanStatus.ERROR and not self.error_type:
            raise ValueError("error spans require error_type")
        return self


class RunTrace(BaseModel):
    run_id: str = Field(min_length=1)
    success: bool
    spans: list[RunSpan] = Field(default_factory=list)
    quality_score: float | None = Field(default=None, ge=0.0, le=1.0)

    @property
    def total_latency_ms(self) -> float:
        return sum(span.duration_ms for span in self.spans)

    @property
    def total_cost_usd(self) -> float:
        return sum(span.cost_usd for span in self.spans)

    @property
    def total_tokens(self) -> int:
        return sum(span.input_tokens + span.output_tokens for span in self.spans)

    def primary_failure_cluster(self) -> str | None:
        for span in self.spans:
            if span.status is SpanStatus.ERROR:
                return f"{span.layer.value}:{span.error_type}"
        if not self.success:
            return "quality:final_answer_failure"
        return None


class BatchSummary(BaseModel):
    run_count: int = Field(ge=0)
    success_rate: float = Field(ge=0.0, le=1.0)
    average_latency_ms: float = Field(ge=0)
    average_cost_usd: float = Field(ge=0)
    average_tokens: float = Field(ge=0)
    layer_failure_rates: dict[SpanLayer, float] = Field(default_factory=dict)
    failure_clusters: dict[str, int] = Field(default_factory=dict)
    average_quality_score: float | None = Field(default=None, ge=0.0, le=1.0)


class RegressionPolicy(BaseModel):
    maximum_success_drop: float = Field(default=0.05, ge=0.0, le=1.0)
    maximum_layer_failure_increase: float = Field(default=0.05, ge=0.0, le=1.0)
    maximum_latency_ratio: float = Field(default=1.30, ge=1.0)
    maximum_cost_ratio: float = Field(default=1.30, ge=1.0)
    maximum_quality_drop: float = Field(default=0.08, ge=0.0, le=1.0)


class RegressionDiagnosis(BaseModel):
    degraded: bool
    success_delta: float
    latency_ratio: float
    cost_ratio: float
    quality_delta: float | None = None
    layer_failure_deltas: dict[SpanLayer, float] = Field(default_factory=dict)
    top_failure_clusters: list[tuple[str, int]] = Field(default_factory=list)
    suspects: list[str] = Field(default_factory=list)


class ProductionRunAnalyzer:
    """Turn Run traces into an operational diagnosis instead of a final-score guess."""

    def summarize(self, traces: list[RunTrace]) -> BatchSummary:
        if not traces:
            return BatchSummary(
                run_count=0,
                success_rate=0.0,
                average_latency_ms=0.0,
                average_cost_usd=0.0,
                average_tokens=0.0,
            )

        layer_failures: dict[SpanLayer, set[str]] = defaultdict(set)
        clusters: Counter[str] = Counter()
        quality_scores: list[float] = []

        for trace in traces:
            if trace.quality_score is not None:
                quality_scores.append(trace.quality_score)
            cluster = trace.primary_failure_cluster()
            if cluster:
                clusters[cluster] += 1
            for span in trace.spans:
                if span.status is SpanStatus.ERROR:
                    layer_failures[span.layer].add(trace.run_id)

        return BatchSummary(
            run_count=len(traces),
            success_rate=sum(trace.success for trace in traces) / len(traces),
            average_latency_ms=mean(trace.total_latency_ms for trace in traces),
            average_cost_usd=mean(trace.total_cost_usd for trace in traces),
            average_tokens=mean(trace.total_tokens for trace in traces),
            layer_failure_rates={
                layer: len(run_ids) / len(traces)
                for layer, run_ids in layer_failures.items()
            },
            failure_clusters=dict(clusters),
            average_quality_score=(mean(quality_scores) if quality_scores else None),
        )

    def diagnose(
        self,
        baseline: list[RunTrace],
        current: list[RunTrace],
        *,
        policy: RegressionPolicy | None = None,
    ) -> RegressionDiagnosis:
        rules = policy or RegressionPolicy()
        before = self.summarize(baseline)
        after = self.summarize(current)
        if not baseline or not current:
            raise ValueError("baseline and current batches must be non-empty")

        layers = set(before.layer_failure_rates) | set(after.layer_failure_rates)
        layer_deltas = {
            layer: after.layer_failure_rates.get(layer, 0.0)
            - before.layer_failure_rates.get(layer, 0.0)
            for layer in layers
        }
        success_delta = after.success_rate - before.success_rate
        latency_ratio = self._ratio(after.average_latency_ms, before.average_latency_ms)
        cost_ratio = self._ratio(after.average_cost_usd, before.average_cost_usd)
        quality_delta = None
        if before.average_quality_score is not None and after.average_quality_score is not None:
            quality_delta = after.average_quality_score - before.average_quality_score

        suspects: list[str] = []
        for layer, delta in sorted(layer_deltas.items(), key=lambda item: item[1], reverse=True):
            if delta > rules.maximum_layer_failure_increase:
                suspects.append(
                    f"{layer.value} failure rate increased by {delta:.1%}"
                )
        if latency_ratio > rules.maximum_latency_ratio:
            suspects.append(f"latency increased to {latency_ratio:.2f}x baseline")
        if cost_ratio > rules.maximum_cost_ratio:
            suspects.append(f"cost increased to {cost_ratio:.2f}x baseline")
        if quality_delta is not None and quality_delta < -rules.maximum_quality_drop:
            suspects.append(f"quality score dropped by {abs(quality_delta):.3f}")
        if success_delta < -rules.maximum_success_drop and not suspects:
            suspects.append("success regressed without an operational error spike; inspect quality evals")

        degraded = bool(suspects) or success_delta < -rules.maximum_success_drop
        top_clusters = sorted(
            after.failure_clusters.items(),
            key=lambda item: (-item[1], item[0]),
        )[:5]
        return RegressionDiagnosis(
            degraded=degraded,
            success_delta=success_delta,
            latency_ratio=latency_ratio,
            cost_ratio=cost_ratio,
            quality_delta=quality_delta,
            layer_failure_deltas=layer_deltas,
            top_failure_clusters=top_clusters,
            suspects=suspects,
        )

    @staticmethod
    def _ratio(current: float, baseline: float) -> float:
        if baseline == 0:
            return 1.0 if current == 0 else float("inf")
        return current / baseline


def _ok_run(index: int, *, quality: float = 0.93) -> RunTrace:
    return RunTrace(
        run_id=f"run-{index:03d}",
        success=True,
        quality_score=quality,
        spans=[
            RunSpan(name="invoke_agent", layer=SpanLayer.AGENT, duration_ms=40),
            RunSpan(
                name="retrieve",
                layer=SpanLayer.RETRIEVAL,
                duration_ms=90,
                attributes={"documents": 6},
            ),
            RunSpan(
                name="chat",
                layer=SpanLayer.MODEL,
                duration_ms=320,
                input_tokens=1200,
                output_tokens=350,
                cost_usd=0.012,
                attributes={"model": "teaching-model"},
            ),
            RunSpan(name="execute_tool", layer=SpanLayer.TOOL, duration_ms=80),
        ],
    )


def build_success_drop_incident() -> tuple[list[RunTrace], list[RunTrace]]:
    """Deterministic A4 fixture: baseline 92% success, current 78% success.

    The additional 14 failures are concentrated in a paper-search tool timeout,
    giving the analyzer a concrete layer/cluster to identify.
    """

    baseline: list[RunTrace] = []
    current: list[RunTrace] = []
    for index in range(100):
        if index < 92:
            baseline.append(_ok_run(index))
        else:
            failed = _ok_run(index)
            failed.success = False
            failed.quality_score = 0.35
            failed.spans[-1] = RunSpan(
                name="execute_tool",
                layer=SpanLayer.TOOL,
                duration_ms=180,
                status=SpanStatus.ERROR,
                error_type="search_timeout",
            )
            baseline.append(failed)

        if index < 78:
            current.append(_ok_run(index + 100, quality=0.91))
        else:
            failed = _ok_run(index + 100, quality=0.30)
            failed.success = False
            failed.spans[-1] = RunSpan(
                name="execute_tool",
                layer=SpanLayer.TOOL,
                duration_ms=900,
                status=SpanStatus.ERROR,
                error_type="search_timeout",
            )
            current.append(failed)
    return baseline, current
