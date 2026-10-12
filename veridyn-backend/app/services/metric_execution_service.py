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
    if test_case is None:
        raise ValueError("test_case cannot be None.")
    if test_run is None:
        raise ValueError("test_run cannot be None.")

    context = MetricContext(
        expected_behavior=getattr(test_case, "expected_behavior", None),
        actual_output=getattr(test_run, "actual_output", None),
        latency_ms=getattr(test_run, "latency_ms", None),
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


def execute_metrics_as_dicts(
    test_case: TestCase,
    test_run: TestRun,
) -> list[dict]:
    return [
        result.to_dict()
        for result in execute_metrics(
            test_case,
            test_run,
        )
    ]

