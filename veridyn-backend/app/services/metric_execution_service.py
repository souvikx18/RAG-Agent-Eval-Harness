from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.services.metrics.registry import metric_registry


def execute_metrics(
    test_case: TestCase,
    test_run: TestRun,
) -> list[dict]:
    """
    Execute all currently registered metrics for a TestRun.
    """

    results = []

    correctness_metric = metric_registry.get("correctness")
    correctness_result = correctness_metric.evaluate(
        test_case.expected_behavior,
        test_run.actual_output,
    )

    results.append(
        {
            "metric_name": correctness_result.metric_name,
            "score": correctness_result.score,
            "status": correctness_result.status,
            "explanation": correctness_result.explanation,
        }
    )

    latency_metric = metric_registry.get("latency")
    latency_result = latency_metric.evaluate(
        None,
        test_run.actual_output,
        test_run.latency_ms,
    )

    results.append(
        {
            "metric_name": latency_result.metric_name,
            "score": latency_result.score,
            "status": latency_result.status,
            "explanation": latency_result.explanation,
        }
    )

    return results
