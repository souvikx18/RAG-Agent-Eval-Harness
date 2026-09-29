from app.services.metrics.base_metric import (
    MetricExecutionResult,
    MetricResult,
)


def create_metric_result() -> MetricResult:
    return MetricResult(
        metric_name="latency",
        score=1.0,
        status="passed",
        explanation="Metric passed.",
    )


def test_execution_result_copies_configuration():
    original_configuration = {
        "thresholds": {
            "fast": 500,
            "acceptable": 1000,
        }
    }

    result = MetricExecutionResult(
        metric_result=create_metric_result(),
        configuration_version=1,
        configuration=original_configuration,
    )

    original_configuration["thresholds"]["fast"] = 9999

    assert (
        result.configuration["thresholds"]["fast"]
        == 500
    )


def test_execution_result_configuration_is_independent():
    result = MetricExecutionResult(
        metric_result=create_metric_result(),
        configuration_version=1,
        configuration={
            "thresholds": {
                "fast": 500,
            }
        },
    )

    result.configuration["thresholds"]["fast"] = 9999

    assert result.configuration["thresholds"]["fast"] == 9999
