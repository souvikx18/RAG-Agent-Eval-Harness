from dataclasses import dataclass

from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.services.metric_execution_service import execute_metrics
from app.services.metrics.base_metric import Metric, MetricContext, MetricResult
from app.services.metrics.registry import metric_registry


@dataclass
class FailingMetric(Metric):
    @property
    def name(self) -> str:
        return "failing_metric"

    def evaluate(self, context: MetricContext) -> MetricResult:
        raise RuntimeError("Intentional metric failure")


def test_metric_execution_converts_exception_to_failed_result():
    try:
        metric_registry.register(FailingMetric())

        test_case = TestCase(
            input_data="Test input",
            expected_behavior="Expected output",
        )

        test_run = TestRun(
            actual_output="Expected output",
            latency_ms=100,
        )

        results = execute_metrics(test_case, test_run)

        failing_result = next(
            result
            for result in results
            if result.metric_result.metric_name == "failing_metric"
        )

        assert failing_result.metric_result.score == 0.0
        assert failing_result.metric_result.status == "failed"
        assert (
            failing_result.metric_result.explanation
            == "Metric execution failed: Intentional metric failure"
        )
        assert failing_result.configuration_version == 1
        assert failing_result.configuration == {}

    finally:
        metric_registry.reset()


def test_metric_failure_does_not_stop_other_metrics():
    try:
        metric_registry.register(FailingMetric())

        test_case = TestCase(
            input_data="Test input",
            expected_behavior="Expected output",
        )

        test_run = TestRun(
            actual_output="Expected output",
            latency_ms=100,
        )

        results = execute_metrics(test_case, test_run)

        metric_names = {
            result.metric_result.metric_name
            for result in results
        }

        assert "correctness" in metric_names
        assert "latency" in metric_names
        assert "failing_metric" in metric_names

    finally:
        metric_registry.reset()
