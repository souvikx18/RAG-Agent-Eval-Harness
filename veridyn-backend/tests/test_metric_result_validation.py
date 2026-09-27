import pytest

from app.services.metrics.base_metric import MetricResult


def test_metric_result_accepts_valid_values():
    result = MetricResult(
        metric_name="correctness",
        score=0.75,
        status="passed",
        explanation="Metric passed.",
    )

    assert result.score == 0.75


def test_metric_result_rejects_score_above_one():
    with pytest.raises(
        ValueError,
        match="between 0.0 and 1.0",
    ):
        MetricResult(
            metric_name="correctness",
            score=1.1,
            status="passed",
            explanation="Invalid score.",
        )


def test_metric_result_rejects_negative_score():
    with pytest.raises(
        ValueError,
        match="between 0.0 and 1.0",
    ):
        MetricResult(
            metric_name="correctness",
            score=-0.1,
            status="failed",
            explanation="Invalid score.",
        )


def test_metric_result_rejects_empty_metric_name():
    with pytest.raises(
        ValueError,
        match="Metric name cannot be empty",
    ):
        MetricResult(
            metric_name="",
            score=1.0,
            status="passed",
            explanation="Valid explanation.",
        )


def test_metric_result_rejects_invalid_status():
    with pytest.raises(
        ValueError,
        match="Metric status must be",
    ):
        MetricResult(
            metric_name="correctness",
            score=1.0,
            status="unknown",
            explanation="Invalid status.",
        )


def test_metric_result_rejects_empty_explanation():
    with pytest.raises(
        ValueError,
        match="Metric explanation cannot be empty",
    ):
        MetricResult(
            metric_name="correctness",
            score=1.0,
            status="passed",
            explanation="",
        )
