import pytest

from app.services.metrics.base_metric import (
    MetricExecutionResult,
    MetricResult,
)


def create_metric_result() -> MetricResult:
    return MetricResult(
        metric_name="correctness",
        score=1.0,
        status="passed",
        explanation="Metric passed.",
    )


def test_metric_execution_result_accepts_valid_values():
    result = MetricExecutionResult(
        metric_result=create_metric_result(),
        configuration_version=1,
        configuration={
            "case_sensitive": False,
        },
    )

    assert result.configuration_version == 1
    assert result.configuration == {
        "case_sensitive": False,
    }


def test_metric_execution_result_accepts_higher_version():
    result = MetricExecutionResult(
        metric_result=create_metric_result(),
        configuration_version=10,
        configuration={},
    )

    assert result.configuration_version == 10


def test_metric_execution_result_rejects_zero_version():
    with pytest.raises(
        ValueError,
        match="Configuration version must be at least 1",
    ):
        MetricExecutionResult(
            metric_result=create_metric_result(),
            configuration_version=0,
            configuration={},
        )


def test_metric_execution_result_rejects_negative_version():
    with pytest.raises(
        ValueError,
        match="Configuration version must be at least 1",
    ):
        MetricExecutionResult(
            metric_result=create_metric_result(),
            configuration_version=-1,
            configuration={},
        )


def test_metric_execution_result_rejects_none_configuration():
    with pytest.raises(
        TypeError,
        match="Metric configuration must be a dictionary",
    ):
        MetricExecutionResult(
            metric_result=create_metric_result(),
            configuration_version=1,
            configuration=None,
        )


def test_metric_execution_result_rejects_non_dictionary_configuration():
    with pytest.raises(
        TypeError,
        match="Metric configuration must be a dictionary",
    ):
        MetricExecutionResult(
            metric_result=create_metric_result(),
            configuration_version=1,
            configuration="invalid",
        )
