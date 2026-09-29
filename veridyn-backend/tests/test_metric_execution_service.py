import uuid

from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.services.metric_execution_service import (
    execute_metrics,
    execute_metrics_as_dicts,
)
from app.services.metrics.registry import metric_registry


def test_execute_metrics_returns_correctness_and_latency():
    test_case = TestCase(
        evaluation_id=uuid.uuid4(),
        name="Metric Execution Test",
        category="functional",
        input_data="Hello",
        expected_behavior="helpful greeting",
        is_adversarial=False,
    )

    test_run = TestRun(
        test_case_id=test_case.id,
        status="completed",
        actual_output="Hello! This is a helpful greeting.",
        latency_ms=200,
        result="passed",
    )

    results = execute_metrics(
        test_case,
        test_run,
    )

    assert len(results) == 2

    metric_names = {
        result.metric_result.metric_name
        for result in results
    }

    assert metric_names == {
        "correctness",
        "latency",
    }


def test_execute_metrics_returns_expected_scores():
    test_case = TestCase(
        evaluation_id=uuid.uuid4(),
        name="Metric Score Test",
        category="functional",
        input_data="Hello",
        expected_behavior="helpful greeting",
        is_adversarial=False,
    )

    test_run = TestRun(
        test_case_id=test_case.id,
        status="completed",
        actual_output="This is a helpful greeting.",
        latency_ms=500,
        result="passed",
    )

    results = execute_metrics(
        test_case,
        test_run,
    )

    results_by_name = {
        result.metric_result.metric_name: result.metric_result
        for result in results
    }

    assert results_by_name["correctness"].score == 1.0
    assert results_by_name["latency"].score == 1.0


def test_execute_metrics_handles_failed_output():
    test_case = TestCase(
        evaluation_id=uuid.uuid4(),
        name="Failed Metric Test",
        category="reliability",
        input_data="Hello",
        expected_behavior="helpful greeting",
        is_adversarial=False,
    )

    test_run = TestRun(
        test_case_id=test_case.id,
        status="completed",
        actual_output=None,
        latency_ms=None,
        result="failed",
    )

    results = execute_metrics(
        test_case,
        test_run,
    )

    results_by_name = {
        result.metric_result.metric_name: result.metric_result
        for result in results
    }

    assert results_by_name["correctness"].score == 0.0
    assert results_by_name["latency"].score == 0.0


def test_metric_execution_includes_configuration_snapshot():
    metric_registry.reset()

    test_case = TestCase(
        input_data="Test input",
        expected_behavior="Expected output",
    )

    test_run = TestRun(
        actual_output="Expected output",
        latency_ms=100,
    )

    results = execute_metrics(
        test_case,
        test_run,
    )

    correctness_result = next(
        result
        for result in results
        if result.metric_result.metric_name == "correctness"
    )

    latency_result = next(
        result
        for result in results
        if result.metric_result.metric_name == "latency"
    )

    assert correctness_result.configuration_version == 1
    assert correctness_result.configuration == {
        "case_sensitive": False,
    }

    assert latency_result.configuration_version == 1
    assert latency_result.configuration == {
        "fast_threshold_ms": 500,
        "acceptable_threshold_ms": 1000,
        "high_threshold_ms": 2000,
    }


def test_metric_execution_reflects_configured_metric():
    metric_registry.reset()
    original_correctness = metric_registry.get(
        "correctness"
    ).get_configuration()

    try:
        metric_registry.configure(
            "correctness",
            {
                "case_sensitive": True,
            },
        )

        test_case = TestCase(
            input_data="Test input",
            expected_behavior="Hello",
        )

        test_run = TestRun(
            actual_output="hello",
            latency_ms=100,
        )

        results = execute_metrics(
            test_case,
            test_run,
        )

        correctness_result = next(
            result
            for result in results
            if result.metric_result.metric_name == "correctness"
        )

        assert (
            correctness_result.configuration_version
            == 2
        )

        assert correctness_result.configuration == {
            "case_sensitive": True,
        }

        assert correctness_result.metric_result.score == 0.0

    finally:
        metric_registry.reset()


def test_execute_metrics_as_dicts_returns_serialized_results():
    test_case = TestCase(
        input_data="Test input",
        expected_behavior="Expected output",
    )

    test_run = TestRun(
        actual_output="Expected output",
        latency_ms=100,
    )

    results = execute_metrics_as_dicts(
        test_case,
        test_run,
    )

    correctness_result = next(
        result
        for result in results
        if result["metric_name"] == "correctness"
    )

    assert correctness_result["score"] == 1.0
    assert correctness_result["status"] == "passed"
    assert correctness_result["configuration_version"] == 1
    assert correctness_result["configuration"] == {
        "case_sensitive": False,
    }


def test_execute_metrics_as_dicts_matches_execution_results():
    test_case = TestCase(
        input_data="Test input",
        expected_behavior="Expected output",
    )

    test_run = TestRun(
        actual_output="Expected output",
        latency_ms=100,
    )

    object_results = execute_metrics(
        test_case,
        test_run,
    )

    dictionary_results = execute_metrics_as_dicts(
        test_case,
        test_run,
    )

    expected = [
        result.to_dict()
        for result in object_results
    ]

    assert dictionary_results == expected


