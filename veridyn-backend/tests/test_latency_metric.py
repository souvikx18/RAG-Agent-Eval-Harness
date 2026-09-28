import pytest

from app.services.metrics.base_metric import MetricContext
from app.services.metrics.latency_metric import LatencyMetric


def test_latency_metric_within_target():
    metric = LatencyMetric()

    result = metric.evaluate(
        MetricContext(
            expected_behavior=None,
            actual_output=None,
            latency_ms=500,
        )
    )

    assert metric.name == "latency"
    assert result.metric_name == "latency"
    assert result.score == 1.0
    assert result.status == "passed"


def test_latency_metric_acceptable():
    metric = LatencyMetric()

    result = metric.evaluate(
        MetricContext(
            expected_behavior=None,
            actual_output=None,
            latency_ms=1000,
        )
    )

    assert result.score == 0.75
    assert result.status == "passed"


def test_latency_metric_high():
    metric = LatencyMetric()

    result = metric.evaluate(
        MetricContext(
            expected_behavior=None,
            actual_output=None,
            latency_ms=2000,
        )
    )

    assert result.score == 0.5
    assert result.status == "failed"


def test_latency_metric_exceeds_target():
    metric = LatencyMetric()

    result = metric.evaluate(
        MetricContext(
            expected_behavior=None,
            actual_output=None,
            latency_ms=2001,
        )
    )

    assert result.score == 0.0
    assert result.status == "failed"


def test_latency_metric_missing():
    metric = LatencyMetric()

    result = metric.evaluate(
        MetricContext(
            expected_behavior=None,
            actual_output=None,
            latency_ms=None,
        )
    )

    assert result.score == 0.0
    assert result.status == "failed"


def test_latency_metric_default_configuration():
    metric = LatencyMetric()

    assert metric.fast_threshold_ms == 500
    assert metric.acceptable_threshold_ms == 1000
    assert metric.high_threshold_ms == 2000


def test_latency_metric_can_be_configured():
    metric = LatencyMetric()

    metric.configure(
        {
            "fast_threshold_ms": 300,
            "acceptable_threshold_ms": 600,
            "high_threshold_ms": 1200,
        }
    )

    assert metric.fast_threshold_ms == 300
    assert metric.acceptable_threshold_ms == 600
    assert metric.high_threshold_ms == 1200


def test_latency_metric_uses_custom_configuration():
    metric = LatencyMetric()

    metric.configure(
        {
            "fast_threshold_ms": 300,
            "acceptable_threshold_ms": 600,
            "high_threshold_ms": 1200,
        }
    )

    result = metric.evaluate(
        MetricContext(
            expected_behavior=None,
            actual_output="output",
            latency_ms=300,
        )
    )

    assert result.score == 1.0
    assert result.status == "passed"


def test_latency_metric_rejects_invalid_threshold_order():
    metric = LatencyMetric()

    with pytest.raises(
        ValueError,
        match="acceptable_threshold_ms must be greater",
    ):
        metric.configure(
            {
                "fast_threshold_ms": 1000,
                "acceptable_threshold_ms": 500,
                "high_threshold_ms": 2000,
            }
        )


def test_latency_metric_rejects_negative_threshold():
    metric = LatencyMetric()

    with pytest.raises(
        ValueError,
        match="fast_threshold_ms cannot be negative",
    ):
        metric.configure(
            {
                "fast_threshold_ms": -1,
                "acceptable_threshold_ms": 1000,
                "high_threshold_ms": 2000,
            }
        )
