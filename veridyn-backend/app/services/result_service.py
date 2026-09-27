from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.evaluation_result import EvaluationResult
from app.models.test_run import TestRun
from app.models.test_case import TestCase

from app.services.metrics.correctness_metric import CorrectnessMetric
from app.services.metrics.latency_metric import LatencyMetric


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
        .filter(
            TestCase.id == test_run.test_case_id
        )
        .first()
    )

    if not test_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test case not found",
        )

    results = []

    correctness_metric = CorrectnessMetric()
    latency_metric = LatencyMetric()

    if test_run.status == "failed":

        correctness_result = correctness_metric.evaluate(
            test_case.expected_behavior,
            None,
        )

        latency_result = latency_metric.evaluate(
            None,
            None,
            None,
        )

        results.append(
            EvaluationResult(
                test_run_id=test_run.id,
                metric_name=correctness_result.metric_name,
                score=0.0,
                status="failed",
                explanation=(
                    test_run.error_message
                    or "Agent execution failed."
                ),
            )
        )

        results.append(
            EvaluationResult(
                test_run_id=test_run.id,
                metric_name=latency_result.metric_name,
                score=0.0,
                status="failed",
                explanation=(
                    "Latency could not be evaluated "
                    "because agent execution failed."
                ),
            )
        )

    else:

        correctness_result = correctness_metric.evaluate(
            test_case.expected_behavior,
            test_run.actual_output,
        )

        latency_result = latency_metric.evaluate(
            None,
            test_run.actual_output,
            test_run.latency_ms,
        )

        results.append(
            EvaluationResult(
                test_run_id=test_run.id,
                metric_name=correctness_result.metric_name,
                score=correctness_result.score,
                status=correctness_result.status,
                explanation=correctness_result.explanation,
            )
        )

        results.append(
            EvaluationResult(
                test_run_id=test_run.id,
                metric_name=latency_result.metric_name,
                score=latency_result.score,
                status=latency_result.status,
                explanation=latency_result.explanation,
            )
        )

    db.add_all(results)
    db.commit()

    for result in results:
        db.refresh(result)

    return results