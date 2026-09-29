from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.services.metrics.base_metric import MetricContext
from app.services.metrics.registry import metric_registry


def execute_metrics(
    test_case: TestCase,
    test_run: TestRun,
) -> list[dict]:
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
            results.append(
                {
                    "metric_name": metric.name,
                    "score": 0.0,
                    "status": "failed",
                    "explanation": (
                        f"Metric execution failed: {str(exc)}"
                    ),
                    "configuration_version": (
                        metric.get_configuration_version()
                    ),
                    "configuration": (
                        metric.get_configuration()
                    ),
                }
            )
            continue

        results.append(
            {
                "metric_name": metric_result.metric_name,
                "score": metric_result.score,
                "status": metric_result.status,
                "explanation": metric_result.explanation,
                "configuration_version": (
                    metric.get_configuration_version()
                ),
                "configuration": (
                    metric.get_configuration()
                ),
            }
        )

    return results
