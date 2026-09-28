import pytest

from app.services.metrics.base_metric import MetricContext
from app.services.metrics.correctness_metric import CorrectnessMetric


def test_correctness_metric_passes_when_expected_behavior_is_found():
    metric = CorrectnessMetric()

    result = metric.evaluate(
        MetricContext(
            expected_behavior="helpful greeting",
            actual_output="Hello! This is a helpful greeting.",
            latency_ms=200,
        )
    )

    assert metric.name == "correctness"
    assert result.metric_name == "correctness"
    assert result.score == 1.0
    assert result.status == "passed"


def test_correctness_metric_fails_when_expected_behavior_is_missing():
    metric = CorrectnessMetric()

    result = metric.evaluate(
        MetricContext(
            expected_behavior="helpful greeting",
            actual_output="I cannot help with that.",
            latency_ms=200,
        )
    )

    assert result.score == 0.0
    assert result.status == "failed"


def test_correctness_metric_fails_without_actual_output():
    metric = CorrectnessMetric()

    result = metric.evaluate(
        MetricContext(
            expected_behavior="helpful greeting",
            actual_output=None,
            latency_ms=None,
        )
    )

    assert result.score == 0.0
    assert result.status == "failed"


def test_correctness_metric_passes_without_expected_behavior():
    metric = CorrectnessMetric()

    result = metric.evaluate(
        MetricContext(
            expected_behavior=None,
            actual_output="Any response",
            latency_ms=200,
        )
    )

    assert result.score == 1.0
    assert result.status == "passed"


def test_correctness_metric_is_case_insensitive():
    metric = CorrectnessMetric()

    result = metric.evaluate(
        MetricContext(
            expected_behavior="Helpful Greeting",
            actual_output="This is a HELPFUL GREETING.",
            latency_ms=200,
        )
    )

    assert result.score == 1.0
    assert result.status == "passed"


def test_correctness_metric_default_configuration():
    metric = CorrectnessMetric()

    assert metric.case_sensitive is False


def test_correctness_metric_can_enable_case_sensitive_matching():
    metric = CorrectnessMetric()

    metric.configure(
        {
            "case_sensitive": True,
        }
    )

    assert metric.case_sensitive is True


def test_correctness_metric_case_sensitive_matching():
    metric = CorrectnessMetric()

    metric.configure(
        {
            "case_sensitive": True,
        }
    )

    result = metric.evaluate(
        MetricContext(
            expected_behavior="Hello World",
            actual_output="hello world",
            latency_ms=100,
        )
    )

    assert result.score == 0.0
    assert result.status == "failed"


def test_correctness_metric_case_insensitive_by_default():
    metric = CorrectnessMetric()

    result = metric.evaluate(
        MetricContext(
            expected_behavior="Hello World",
            actual_output="hello world",
            latency_ms=100,
        )
    )

    assert result.score == 1.0
    assert result.status == "passed"


def test_correctness_metric_rejects_invalid_configuration():
    metric = CorrectnessMetric()

    with pytest.raises(
        ValueError,
        match="case_sensitive must be a boolean",
    ):
        metric.configure(
            {
                "case_sensitive": "true",
            }
        )
