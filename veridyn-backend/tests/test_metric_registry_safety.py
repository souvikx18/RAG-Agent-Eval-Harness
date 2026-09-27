import pytest

from app.services.metrics.base_metric import Metric, MetricContext, MetricResult
from app.services.metrics.registry import MetricRegistry


class TestMetric(Metric):
    @property
    def name(self) -> str:
        return "test_metric"

    def evaluate(self, context: MetricContext) -> MetricResult:
        return MetricResult(
            metric_name=self.name,
            score=1.0,
            status="passed",
            explanation="Test metric passed.",
        )


class EmptyNameMetric(Metric):
    @property
    def name(self) -> str:
        return ""

    def evaluate(self, context: MetricContext) -> MetricResult:
        return MetricResult(
            metric_name="",
            score=1.0,
            status="passed",
            explanation="Test metric.",
        )


def test_registry_rejects_duplicate_metric():
    registry = MetricRegistry()

    registry.register(TestMetric())

    with pytest.raises(
        ValueError,
        match="already registered",
    ):
        registry.register(TestMetric())


def test_registry_rejects_empty_metric_name():
    registry = MetricRegistry()

    with pytest.raises(
        ValueError,
        match="Metric name cannot be empty",
    ):
        registry.register(EmptyNameMetric())


def test_registry_returns_registered_metric():
    registry = MetricRegistry()

    metric = TestMetric()
    registry.register(metric)

    assert registry.get("test_metric") is metric


def test_registry_rejects_unknown_metric():
    registry = MetricRegistry()

    with pytest.raises(
        ValueError,
        match="Unknown metric",
    ):
        registry.get("does_not_exist")
