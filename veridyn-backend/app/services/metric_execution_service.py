from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.services.metrics.registry import metric_registry


def execute_metrics(
    test_case: TestCase,
    test_run: TestRun,
) -> list[dict]:
    """
    Execute all registered evaluation metrics for a TestRun.
    """

    results = []

    for metric in metric_registry.all():

        if metric.name == "correctness":
            metric_result = metric.evaluate(
                test_case.expected_behavior,
                test_run.actual_output,
            )

        elif metric.name == "latency":
            metric_result = metric.evaluate(
                None,
                test_run.actual_output,
                test_run.latency_ms,
            )

        else:
            metric_result = metric.evaluate(
                test_case.expected_behavior,
                test_run.actual_output,
            )

        results.append(
            {
                "metric_name": metric_result.metric_name,
                "score": metric_result.score,
                "status": metric_result.status,
                "explanation": metric_result.explanation,
            }
        )

    return results
