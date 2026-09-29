from app.services.metrics.correctness_metric import CorrectnessMetric
from app.services.metrics.latency_metric import LatencyMetric


def test_metric_starts_at_configuration_version_one():
    metric = CorrectnessMetric()

    assert metric.get_configuration_version() == 1


def test_correctness_configuration_increments_version():
    metric = CorrectnessMetric()

    assert metric.get_configuration_version() == 1

    metric.configure(
        {
            "case_sensitive": True,
        }
    )

    assert metric.get_configuration_version() == 2

    metric.configure(
        {
            "case_sensitive": False,
        }
    )

    assert metric.get_configuration_version() == 3


def test_latency_configuration_increments_version():
    metric = LatencyMetric()

    assert metric.get_configuration_version() == 1

    metric.configure(
        {
            "fast_threshold_ms": 300,
        }
    )

    assert metric.get_configuration_version() == 2


def test_failed_configuration_does_not_increment_version():
    metric = LatencyMetric()

    assert metric.get_configuration_version() == 1

    try:
        metric.configure(
            {
                "unknown_setting": 123,
            }
        )
    except ValueError:
        pass

    assert metric.get_configuration_version() == 1


def test_configuration_version_is_independent_between_metrics():
    correctness = CorrectnessMetric()
    latency = LatencyMetric()

    correctness.configure(
        {
            "case_sensitive": True,
        }
    )

    assert correctness.get_configuration_version() == 2
    assert latency.get_configuration_version() == 1
