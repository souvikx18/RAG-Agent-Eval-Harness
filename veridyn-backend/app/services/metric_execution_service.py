from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.services.metrics.base_metric import (
    MetricContext,
    MetricExecutionResult,
    MetricResult,
)
from app.services.metrics.registry import metric_registry


def execute_metrics(
    test_case: TestCase,
    test_run: TestRun,
) -> list[MetricExecutionResult]:
    context = MetricContext(
        expected_behavior=test_case.expected_behavior,
        actual_output=test_run.actual_output,
        latency_ms=test_run.latency_ms,
    )

    results = []

    for metric in metric_registry.all():
        try:
            metric_result = metric.evaluate(context)

        except Exception as exc:
            metric_result = MetricResult(
                metric_name=metric.name,
                score=0.0,
                status="failed",
                explanation=(
                    f"Metric execution failed: {str(exc)}"
                ),
            )

        results.append(
            MetricExecutionResult(
                metric_result=metric_result,
                configuration_version=(
                    metric.get_configuration_version()
                ),
                configuration=(
                    metric.get_configuration()
                ),
            )
        )

    return results
