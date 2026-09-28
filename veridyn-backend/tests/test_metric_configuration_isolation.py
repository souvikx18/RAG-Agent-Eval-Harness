from app.services.metrics.base_metric import MetricContext
from app.services.metrics.registry import MetricRegistry


def test_configuring_correctness_does_not_change_latency():
    registry = MetricRegistry()

    correctness = registry.get("correctness")
    latency = registry.get("latency")

    original_fast_threshold = latency.fast_threshold_ms
    original_acceptable_threshold = latency.acceptable_threshold_ms
    original_high_threshold = latency.high_threshold_ms

    correctness.configure(
        {
            "case_sensitive": True,
        }
    )

    assert correctness.case_sensitive is True

    assert latency.fast_threshold_ms == original_fast_threshold
    assert (
        latency.acceptable_threshold_ms
        == original_acceptable_threshold
    )
    assert (
        latency.high_threshold_ms
        == original_high_threshold
    )


def test_configuring_latency_does_not_change_correctness():
    registry = MetricRegistry()

    correctness = registry.get("correctness")
    latency = registry.get("latency")

    assert correctness.case_sensitive is False

    latency.configure(
        {
            "fast_threshold_ms": 300,
            "acceptable_threshold_ms": 600,
            "high_threshold_ms": 1200,
        }
    )

    assert latency.fast_threshold_ms == 300
    assert latency.acceptable_threshold_ms == 600
    assert latency.high_threshold_ms == 1200

    assert correctness.case_sensitive is False


def test_registry_configures_only_requested_metric():
    registry = MetricRegistry()

    registry.configure(
        "correctness",
        {
            "case_sensitive": True,
        },
    )

    correctness = registry.get("correctness")
    latency = registry.get("latency")

    assert correctness.case_sensitive is True

    assert latency.fast_threshold_ms == 500
    assert latency.acceptable_threshold_ms == 1000
    assert latency.high_threshold_ms == 2000


def test_separate_registries_have_independent_metric_configuration():
    registry_one = MetricRegistry()
    registry_two = MetricRegistry()

    registry_one.configure(
        "correctness",
        {
            "case_sensitive": True,
        },
    )

    registry_one.configure(
        "latency",
        {
            "fast_threshold_ms": 300,
            "acceptable_threshold_ms": 600,
            "high_threshold_ms": 1200,
        },
    )

    correctness_two = registry_two.get("correctness")
    latency_two = registry_two.get("latency")

    assert correctness_two.case_sensitive is False

    assert latency_two.fast_threshold_ms == 500
    assert latency_two.acceptable_threshold_ms == 1000
    assert latency_two.high_threshold_ms == 2000
