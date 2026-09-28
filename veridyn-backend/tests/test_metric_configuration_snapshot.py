from app.services.metrics.base_metric import Metric
from app.services.metrics.correctness_metric import CorrectnessMetric
from app.services.metrics.latency_metric import LatencyMetric


def test_correctness_configuration_snapshot():
    metric = CorrectnessMetric()

    assert metric.get_configuration() == {
        "case_sensitive": False,
    }

    metric.configure(
        {
            "case_sensitive": True,
        }
    )

    assert metric.get_configuration() == {
        "case_sensitive": True,
    }


def test_latency_configuration_snapshot():
    metric = LatencyMetric()

    assert metric.get_configuration() == {
        "fast_threshold_ms": 500,
        "acceptable_threshold_ms": 1000,
        "high_threshold_ms": 2000,
    }

    metric.configure(
        {
            "fast_threshold_ms": 300,
            "acceptable_threshold_ms": 600,
            "high_threshold_ms": 1200,
        }
    )

    assert metric.get_configuration() == {
        "fast_threshold_ms": 300,
        "acceptable_threshold_ms": 600,
        "high_threshold_ms": 1200,
    }


def test_configuration_snapshot_is_independent():
    metric = LatencyMetric()

    configuration = metric.get_configuration()

    configuration["fast_threshold_ms"] = 9999

    assert metric.fast_threshold_ms == 500


def test_base_metric_default_configuration():
    class SimpleMetric(Metric):
        @property
        def name(self) -> str:
            return "simple"

        def evaluate(self, context):
            raise NotImplementedError

    metric = SimpleMetric()

    assert metric.get_configuration() == {}
