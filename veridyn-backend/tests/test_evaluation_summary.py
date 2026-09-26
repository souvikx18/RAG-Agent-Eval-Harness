from unittest.mock import MagicMock, patch
import pytest
from app.main import app
from app.models.evaluation import Evaluation
from app.models.test_run import TestRun
from app.services.evaluation_service import build_evaluation_summary, complete_evaluation


def test_build_evaluation_summary_all_passed():
    run1 = TestRun(status="completed", result="passed")
    run2 = TestRun(status="completed", result="passed")
    summary = build_evaluation_summary(1.0, [run1, run2])
    assert summary == "Evaluation completed with overall score: 1.00. Total test runs: 2. Passed: 2. Failed: 0."


def test_build_evaluation_summary_all_failed():
    run1 = TestRun(status="failed", result="failed")
    summary = build_evaluation_summary(0.0, [run1])
    assert summary == "Evaluation completed with overall score: 0.00. Total test runs: 1. Passed: 0. Failed: 1."


def test_build_evaluation_summary_mixed():
    run1 = TestRun(status="completed", result="passed")
    run2 = TestRun(status="failed", result="failed")
    summary = build_evaluation_summary(0.5, [run1, run2])
    assert summary == "Evaluation completed with overall score: 0.50. Total test runs: 2. Passed: 1. Failed: 1."


def test_complete_evaluation_custom_summary():
    mock_db = MagicMock()
    eval_obj = Evaluation(id="test-eval-1", status="running")
    test_run = TestRun(status="completed", result="passed")

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
    test_run = TestRun(status="completed", result="passed")

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
            == "Evaluation completed with overall score: 1.00. Total test runs: 1. Passed: 1. Failed: 0."
        )
        assert completed_eval.status == "completed"
        assert completed_eval.overall_score == 1.0
