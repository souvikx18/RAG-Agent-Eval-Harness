from app.services.metrics.latency_metric import LatencyMetric


def test_latency_metric_within_target():
    metric = LatencyMetric()

    result = metric.evaluate(
        None,
        None,
        500,
    )

    assert metric.name == "latency"
    assert result.metric_name == "latency"
    assert result.score == 1.0
    assert result.status == "passed"


def test_latency_metric_acceptable():
    metric = LatencyMetric()

    result = metric.evaluate(
        None,
        None,
        1000,
    )

    assert result.score == 0.75
    assert result.status == "passed"


def test_latency_metric_high():
    metric = LatencyMetric()

    result = metric.evaluate(
        None,
        None,
        2000,
    )

    assert result.score == 0.5
    assert result.status == "failed"


def test_latency_metric_exceeds_target():
    metric = LatencyMetric()

    result = metric.evaluate(
        None,
        None,
        2001,
    )

    assert result.score == 0.0
    assert result.status == "failed"


def test_latency_metric_missing():
    metric = LatencyMetric()

    result = metric.evaluate(
        None,
        None,
        None,
    )

    assert result.score == 0.0
    assert result.status == "failed"
