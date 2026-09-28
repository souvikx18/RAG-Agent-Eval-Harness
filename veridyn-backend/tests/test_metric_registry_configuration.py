from typing import Any

import pytest

from app.services.metrics.base_metric import (
    Metric,
    MetricContext,
    MetricResult,
)
from app.services.metrics.registry import MetricRegistry


def test_registry_returns_all_metric_configurations():
    registry = MetricRegistry()

    configs = registry.get_configurations()

    assert set(configs.keys()) == {"correctness", "latency"}

    assert configs["correctness"] == {
        "case_sensitive": False,
    }

    assert configs["latency"] == {
        "fast_threshold_ms": 500,
        "acceptable_threshold_ms": 1000,
        "high_threshold_ms": 2000,
    }


def test_registry_configuration_snapshot_reflects_changes():
    registry = MetricRegistry()

    registry.configure(
        "latency",
        {
            "fast_threshold_ms": 400,
            "acceptable_threshold_ms": 800,
            "high_threshold_ms": 1600,
        },
    )

    configs = registry.get_configurations()

    assert configs["latency"] == {
        "fast_threshold_ms": 400,
        "acceptable_threshold_ms": 800,
        "high_threshold_ms": 1600,
    }


def test_registry_configuration_snapshot_is_independent():
    registry = MetricRegistry()

    configs = registry.get_configurations()

    configs["latency"]["fast_threshold_ms"] = 9999

    refreshed_configs = registry.get_configurations()

    assert refreshed_configs["latency"]["fast_threshold_ms"] == 500


def test_empty_registry_returns_empty_configuration():
    registry = MetricRegistry(register_defaults=False)

    assert registry.get_configurations() == {}


def test_custom_metric_configuration_is_included():
    class DummyMetric(Metric):
        @property
        def name(self) -> str:
            return "dummy"

        def evaluate(self, context: MetricContext) -> MetricResult:
            return MetricResult(
                metric_name="dummy",
                score=1.0,
                status="PASS",
                explanation="ok",
            )

        def get_configuration(self) -> dict[str, Any]:
            return {"dummy_flag": True}

    registry = MetricRegistry(register_defaults=False)
    registry.register(DummyMetric())

    assert registry.get_configurations() == {
        "dummy": {
            "dummy_flag": True,
        }
    }


def test_registry_rejects_none_configuration():
    registry = MetricRegistry()

    with pytest.raises(
        TypeError,
        match="Metric configuration must be a dictionary",
    ):
        registry.configure(
            "latency",
            None,
        )


def test_registry_rejects_string_configuration():
    registry = MetricRegistry()

    with pytest.raises(
        TypeError,
        match="Metric configuration must be a dictionary",
    ):
        registry.configure(
            "latency",
            "invalid",
        )


def test_registry_rejects_list_configuration():
    registry = MetricRegistry()

    with pytest.raises(
        TypeError,
        match="Metric configuration must be a dictionary",
    ):
        registry.configure(
            "latency",
            [],
        )


def test_invalid_configuration_does_not_change_metric():
    registry = MetricRegistry()

    original_configuration = (
        registry.get("latency").get_configuration()
    )

    with pytest.raises(
        TypeError,
        match="Metric configuration must be a dictionary",
    ):
        registry.configure(
            "latency",
            None,
        )

    assert (
        registry.get("latency").get_configuration()
        == original_configuration
    )


def test_latency_rejects_unknown_configuration_key():
    registry = MetricRegistry()

    with pytest.raises(
        ValueError,
        match="Unknown latency configuration keys",
    ):
        registry.configure(
            "latency",
            {
                "fast_threshold_ms": 300,
                "unknown_setting": 123,
            },
        )


def test_correctness_rejects_unknown_configuration_key():
    registry = MetricRegistry()

    with pytest.raises(
        ValueError,
        match="Unknown correctness configuration keys",
    ):
        registry.configure(
            "correctness",
            {
                "case_sensitive": True,
                "unknown_setting": True,
            },
        )


def test_unknown_configuration_does_not_change_latency():
    registry = MetricRegistry()

    original = registry.get(
        "latency"
    ).get_configuration()

    with pytest.raises(
        ValueError,
        match="Unknown latency configuration keys",
    ):
        registry.configure(
            "latency",
            {
                "invalid_threshold": 100,
            },
        )

    assert (
        registry.get("latency").get_configuration()
        == original
    )


def test_unknown_configuration_does_not_change_correctness():
    registry = MetricRegistry()

    original = registry.get(
        "correctness"
    ).get_configuration()

    with pytest.raises(
        ValueError,
        match="Unknown correctness configuration keys",
    ):
        registry.configure(
            "correctness",
            {
                "invalid_option": True,
            },
        )

    assert (
        registry.get("correctness").get_configuration()
        == original
    )

