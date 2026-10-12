import logging
import time

from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.services.metrics.base_metric import (
    MetricContext,
    MetricExecutionResult,
    MetricResult,
)
from app.services.metrics.registry import metric_registry

logger = logging.getLogger("veridyn.metrics")


def execute_metrics(
    test_case: TestCase,
    test_run: TestRun,
) -> list[MetricExecutionResult]:
    if test_case is None:
        raise ValueError("test_case cannot be None.")
    if test_run is None:
        raise ValueError("test_run cannot be None.")

    test_run_id = getattr(test_run, "id", None)
    logger.info(
        "Metric evaluation batch starting: test_run_id=%s metric_count=%d",
        test_run_id,
        len(metric_registry.all()),
    )

    context = MetricContext(
        expected_behavior=getattr(test_case, "expected_behavior", None),
        actual_output=getattr(test_run, "actual_output", None),
        latency_ms=getattr(test_run, "latency_ms", None),
    )

    results = []

    for metric in metric_registry.all():
        start_time = time.perf_counter()
        logger.info(
            "Metric evaluation starting: metric=%s test_run_id=%s",
            metric.name,
            test_run_id,
        )

        try:
            metric_result = metric.evaluate(context)
            duration_ms = (time.perf_counter() - start_time) * 1000

            if metric_result.status == "passed":
                logger.info(
                    "Metric evaluation completed successfully: metric=%s test_run_id=%s status=%s score=%.2f duration_ms=%.2f",
                    metric.name,
                    test_run_id,
                    metric_result.status,
                    metric_result.score,
                    duration_ms,
                )
            else:
                logger.warning(
                    "Metric evaluation failed validation: metric=%s test_run_id=%s status=%s score=%.2f duration_ms=%.2f explanation=%s",
                    metric.name,
                    test_run_id,
                    metric_result.status,
                    metric_result.score,
                    duration_ms,
                    metric_result.explanation,
                )

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "Metric evaluation unexpected exception: metric=%s test_run_id=%s duration_ms=%.2f error=%s",
                metric.name,
                test_run_id,
                duration_ms,
                str(exc),
            )
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

