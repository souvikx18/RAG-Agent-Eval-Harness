from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.evaluation_result import EvaluationResult
from app.models.test_run import TestRun
from app.models.test_case import TestCase
from app.services.metrics_service import (
    calculate_correctness_score,
    calculate_latency_score,
)


def create_evaluation_result(
    test_run: TestRun,
    db: Session,
) -> list[EvaluationResult]:

    existing_results = (
        db.query(EvaluationResult)
        .filter(
            EvaluationResult.test_run_id == test_run.id
        )
        .all()
    )

    if existing_results:
        return existing_results

    if test_run.status not in ["completed", "failed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test run has not finished",
        )

    test_case = (
        db.query(TestCase)
        .filter(TestCase.id == test_run.test_case_id)
        .first()
    )

    if not test_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test case not found",
        )

    results = []

    if test_run.status == "failed":
        results.append(
            EvaluationResult(
                test_run_id=test_run.id,
                metric_name="correctness",
                score=0.0,
                status="failed",
                explanation=test_run.error_message
                or "Test run failed.",
            )
        )

        results.append(
            EvaluationResult(
                test_run_id=test_run.id,
                metric_name="latency",
                score=0.0,
                status="failed",
                explanation="Latency could not be evaluated because execution failed.",
            )
        )

    else:
        correctness_score, correctness_explanation = (
            calculate_correctness_score(
                test_case.expected_behavior,
                test_run.actual_output,
            )
        )

        latency_score, latency_explanation = (
            calculate_latency_score(
                test_run.latency_ms,
            )
        )

        results.append(
            EvaluationResult(
                test_run_id=test_run.id,
                metric_name="correctness",
                score=correctness_score,
                status=(
                    "passed"
                    if correctness_score == 1.0
                    else "failed"
                ),
                explanation=correctness_explanation,
            )
        )

        results.append(
            EvaluationResult(
                test_run_id=test_run.id,
                metric_name="latency",
                score=latency_score,
                status=(
                    "passed"
                    if latency_score >= 0.75
                    else "failed"
                ),
                explanation=latency_explanation,
            )
        )

    db.add_all(results)
    db.commit()

    for result in results:
        db.refresh(result)

    return results