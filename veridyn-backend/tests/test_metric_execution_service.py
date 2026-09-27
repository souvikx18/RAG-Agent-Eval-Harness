import uuid

from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.services.metric_execution_service import execute_metrics


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
        result["metric_name"]
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
        result["metric_name"]: result
        for result in results
    }

    assert results_by_name["correctness"]["score"] == 1.0
    assert results_by_name["latency"]["score"] == 1.0


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
        result["metric_name"]: result
        for result in results
    }

    assert results_by_name["correctness"]["score"] == 0.0
    assert results_by_name["latency"]["score"] == 0.0
