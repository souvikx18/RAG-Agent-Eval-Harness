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


def test_registry_rejects_non_metric_object():
    registry = MetricRegistry()

    with pytest.raises(
        TypeError,
        match="Only Metric instances",
    ):
        registry.register("not_a_metric")


def test_registry_names_returns_metric_names():
    registry = MetricRegistry()

    registry.register(TestMetric())

    names = registry.names()

    assert "correctness" in names
    assert "latency" in names
    assert "test_metric" in names


def test_registry_names_returns_new_list():
    registry = MetricRegistry()

    names = registry.names()

    names.clear()

    assert "correctness" in registry.names()
    assert "latency" in registry.names()


def test_registry_all_returns_new_list():
    registry = MetricRegistry()

    metrics = registry.all()

    metrics.clear()

    assert len(registry.all()) == 2
