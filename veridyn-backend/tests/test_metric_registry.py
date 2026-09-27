import pytest

from app.services.metrics.registry import (
    MetricRegistry,
    metric_registry,
)
from app.services.metrics.correctness_metric import CorrectnessMetric
from app.services.metrics.latency_metric import LatencyMetric


def test_registry_contains_correctness_metric():
    metric = metric_registry.get("correctness")

    assert isinstance(metric, CorrectnessMetric)
    assert metric.name == "correctness"


def test_registry_contains_latency_metric():
    metric = metric_registry.get("latency")

    assert isinstance(metric, LatencyMetric)
    assert metric.name == "latency"


def test_registry_returns_all_registered_metrics():
    registry = MetricRegistry()

    metrics = registry.all()

    names = {metric.name for metric in metrics}

    assert names == {"correctness", "latency"}


def test_registry_can_register_custom_metric():
    class CustomMetric(CorrectnessMetric):
        @property
        def name(self) -> str:
            return "custom"

    registry = MetricRegistry()
    custom_metric = CustomMetric()

    registry.register(custom_metric)

    assert registry.get("custom") is custom_metric


def test_registry_rejects_unknown_metric():
    registry = MetricRegistry()

    with pytest.raises(ValueError, match="Unknown metric"):
        registry.get("unknown")
