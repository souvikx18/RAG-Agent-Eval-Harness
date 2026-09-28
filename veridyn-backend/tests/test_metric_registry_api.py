import pytest

from app.services.metrics.base_metric import (
    Metric,
    MetricContext,
    MetricResult,
)
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


def test_registry_reset_restores_default_metrics():
    registry = MetricRegistry()

    registry.register(TestMetric())

    assert "test_metric" in registry.names()

    registry.reset()

    assert registry.names() == [
        "correctness",
        "latency",
    ]


def test_registry_reset_removes_custom_metrics():
    registry = MetricRegistry()

    registry.register(TestMetric())
    registry.reset()

    with pytest.raises(
        ValueError,
        match="Unknown metric",
    ):
        registry.get("test_metric")


def test_registry_can_start_without_defaults():
    registry = MetricRegistry(
        register_defaults=False
    )

    assert registry.names() == []


def test_registry_without_defaults_can_register_custom_metric():
    registry = MetricRegistry(
        register_defaults=False
    )

    metric = TestMetric()
    registry.register(metric)

    assert registry.get("test_metric") is metric
    assert registry.names() == ["test_metric"]


def test_registry_can_configure_metric():
    registry = MetricRegistry()

    registry.configure(
        "correctness",
        {
            "threshold": 0.8,
        },
    )


def test_registry_configuration_unknown_metric_fails():
    registry = MetricRegistry()

    with pytest.raises(
        ValueError,
        match="Unknown metric",
    ):
        registry.configure(
            "does_not_exist",
            {},
        )
