from unittest.mock import MagicMock, patch
import pytest
from app.main import app
from app.models.evaluation import Evaluation
from app.models.test_run import TestRun
from app.services.evaluation_service import (
    build_evaluation_summary,
    calculate_evaluation_statistics,
    complete_evaluation,
)


def test_calculate_evaluation_statistics():
    run1 = TestRun(status="completed", result="passed", latency_ms=100.0)
    run2 = TestRun(status="completed", result="passed", latency_ms=200.0)
    run3 = TestRun(status="failed", result="failed", latency_ms=None)

    stats = calculate_evaluation_statistics([run1, run2, run3])
    assert stats["total_runs"] == 3
    assert stats["passed_runs"] == 2
    assert stats["failed_runs"] == 1
    assert stats["average_latency_ms"] == 150.0


def test_calculate_evaluation_statistics_empty_latency():
    run1 = TestRun(status="failed", result="failed", latency_ms=None)
    stats = calculate_evaluation_statistics([run1])
    assert stats["total_runs"] == 1
    assert stats["passed_runs"] == 0
    assert stats["failed_runs"] == 1
    assert stats["average_latency_ms"] == 0.0


def test_build_evaluation_summary_all_passed():
    run1 = TestRun(status="completed", result="passed", latency_ms=120.0)
    run2 = TestRun(status="completed", result="passed", latency_ms=160.0)
    summary = build_evaluation_summary(1.0, [run1, run2])
    assert (
        summary
        == "Evaluation completed with overall score: 1.00. Total test runs: 2. Passed: 2. Failed: 0. Average latency: 140.00 ms."
    )


def test_build_evaluation_summary_all_failed():
    run1 = TestRun(status="failed", result="failed", latency_ms=None)
    summary = build_evaluation_summary(0.0, [run1])
    assert (
        summary
        == "Evaluation completed with overall score: 0.00. Total test runs: 1. Passed: 0. Failed: 1. Average latency: 0.00 ms."
    )


def test_build_evaluation_summary_mixed():
    run1 = TestRun(status="completed", result="passed", latency_ms=320.0)
    run2 = TestRun(status="failed", result="failed", latency_ms=None)
    summary = build_evaluation_summary(0.5, [run1, run2])
    assert (
        summary
        == "Evaluation completed with overall score: 0.50. Total test runs: 2. Passed: 1. Failed: 1. Average latency: 320.00 ms."
    )


def test_complete_evaluation_custom_summary():
    mock_db = MagicMock()
    eval_obj = Evaluation(id="test-eval-1", status="running")
    test_run = TestRun(status="completed", result="passed", latency_ms=150.0)

    mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = [test_run]

    with patch("app.services.evaluation_service.calculate_evaluation_score", return_value=1.0), \
         patch("app.services.evaluation_service.create_deployment_gate"):
        completed_eval = complete_evaluation(
            evaluation=eval_obj,
            db=mock_db,
            summary="Custom user summary",
        )
        assert completed_eval.summary == "Custom user summary"
        assert completed_eval.status == "completed"
        assert completed_eval.overall_score == 1.0


def test_complete_evaluation_default_summary():
    mock_db = MagicMock()
    eval_obj = Evaluation(id="test-eval-2", status="running")
    test_run = TestRun(status="completed", result="passed", latency_ms=100.0)

    mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = [test_run]

    with patch("app.services.evaluation_service.calculate_evaluation_score", return_value=1.0), \
         patch("app.services.evaluation_service.create_deployment_gate"):
        completed_eval = complete_evaluation(
            evaluation=eval_obj,
            db=mock_db,
            summary=None,
        )
        assert (
            completed_eval.summary
            == "Evaluation completed with overall score: 1.00. Total test runs: 1. Passed: 1. Failed: 0. Average latency: 100.00 ms."
        )
        assert completed_eval.status == "completed"
        assert completed_eval.overall_score == 1.0
