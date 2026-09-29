from app.services.metrics.base_metric import (
    MetricExecutionResult,
    MetricResult,
)


def create_metric_result() -> MetricResult:
    return MetricResult(
        metric_name="correctness",
        score=0.75,
        status="failed",
        explanation="Partial correctness.",
    )


def test_metric_execution_result_to_dict():
    result = MetricExecutionResult(
        metric_result=create_metric_result(),
        configuration_version=2,
        configuration={
            "case_sensitive": True,
        },
    )

    serialized = result.to_dict()

    assert serialized == {
        "metric_name": "correctness",
        "score": 0.75,
        "status": "failed",
        "explanation": "Partial correctness.",
        "configuration_version": 2,
        "configuration": {
            "case_sensitive": True,
        },
    }


def test_to_dict_returns_independent_configuration():
    result = MetricExecutionResult(
        metric_result=create_metric_result(),
        configuration_version=1,
        configuration={
            "nested": {
                "value": 100,
            }
        },
    )

    serialized = result.to_dict()

    serialized["configuration"]["nested"]["value"] = 999

    assert (
        result.configuration["nested"]["value"]
        == 100
    )
