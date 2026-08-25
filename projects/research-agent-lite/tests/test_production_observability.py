from app.production_observability import (
    ProductionRunAnalyzer,
    RunSpan,
    RunTrace,
    SpanLayer,
    SpanStatus,
    build_success_drop_incident,
)


def test_v65_incident_diagnosis_finds_tool_layer_not_just_final_failure() -> None:
    baseline, current = build_success_drop_incident()
    analyzer = ProductionRunAnalyzer()

    before = analyzer.summarize(baseline)
    after = analyzer.summarize(current)
    diagnosis = analyzer.diagnose(baseline, current)

    assert before.success_rate == 0.92
    assert after.success_rate == 0.78
    assert round(diagnosis.success_delta, 2) == -0.14
    assert diagnosis.degraded is True
    assert diagnosis.layer_failure_deltas[SpanLayer.TOOL] == 0.14
    assert diagnosis.top_failure_clusters[0] == ("tool:search_timeout", 22)
    assert any("tool failure rate increased" in suspect for suspect in diagnosis.suspects)


def test_v65_layer_failure_rate_counts_runs_not_number_of_duplicate_error_spans() -> None:
    trace = RunTrace(
        run_id="run-1",
        success=False,
        spans=[
            RunSpan(
                name="tool-attempt-1",
                layer=SpanLayer.TOOL,
                duration_ms=50,
                status=SpanStatus.ERROR,
                error_type="timeout",
            ),
            RunSpan(
                name="tool-attempt-2",
                layer=SpanLayer.TOOL,
                duration_ms=50,
                status=SpanStatus.ERROR,
                error_type="timeout",
            ),
        ],
    )

    summary = ProductionRunAnalyzer().summarize([trace])

    assert summary.layer_failure_rates[SpanLayer.TOOL] == 1.0
    assert summary.failure_clusters == {"tool:timeout": 1}


def test_v65_quality_eval_can_regress_even_when_operational_spans_are_green() -> None:
    baseline = [
        RunTrace(
            run_id=f"base-{i}",
            success=True,
            quality_score=0.95,
            spans=[RunSpan(name="chat", layer=SpanLayer.MODEL, duration_ms=100)],
        )
        for i in range(20)
    ]
    current = [
        RunTrace(
            run_id=f"current-{i}",
            success=True,
            quality_score=0.72,
            spans=[RunSpan(name="chat", layer=SpanLayer.MODEL, duration_ms=100)],
        )
        for i in range(20)
    ]

    diagnosis = ProductionRunAnalyzer().diagnose(baseline, current)

    assert diagnosis.success_delta == 0
    assert diagnosis.quality_delta is not None
    assert round(diagnosis.quality_delta, 2) == -0.23
    assert any("quality score dropped" in suspect for suspect in diagnosis.suspects)


def test_v65_final_answer_failure_without_span_error_is_clustered_as_quality() -> None:
    failed = RunTrace(
        run_id="quality-failure",
        success=False,
        quality_score=0.2,
        spans=[
            RunSpan(name="retrieve", layer=SpanLayer.RETRIEVAL, duration_ms=80),
            RunSpan(name="chat", layer=SpanLayer.MODEL, duration_ms=200),
        ],
    )

    summary = ProductionRunAnalyzer().summarize([failed])

    assert summary.failure_clusters == {"quality:final_answer_failure": 1}
    assert summary.layer_failure_rates == {}


def test_v65_trace_records_compact_operational_attributes_and_cost_token_rollups() -> None:
    trace = RunTrace(
        run_id="run-compact",
        success=True,
        spans=[
            RunSpan(
                name="chat",
                layer=SpanLayer.MODEL,
                duration_ms=250,
                input_tokens=100,
                output_tokens=40,
                cost_usd=0.01,
                attributes={"model": "teaching-model", "finish_reason": "tool_calls"},
            ),
            RunSpan(
                name="execute_tool",
                layer=SpanLayer.TOOL,
                duration_ms=60,
                attributes={"tool": "search_papers"},
            ),
        ],
    )

    assert trace.total_latency_ms == 310
    assert trace.total_tokens == 140
    assert trace.total_cost_usd == 0.01
    assert "prompt" not in trace.spans[0].attributes
    assert "tool_arguments" not in trace.spans[1].attributes
