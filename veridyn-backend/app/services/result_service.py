import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.evaluation_result import EvaluationResult
from app.models.test_run import TestRun
from app.models.test_case import TestCase
from app.services.metric_execution_service import execute_metrics

logger = logging.getLogger("veridyn.evaluation_results")


def create_evaluation_result(
    test_run: TestRun,
    db: Session,
) -> list[EvaluationResult]:
    if test_run is None:
        raise ValueError("test_run cannot be None.")
    if db is None:
        raise ValueError("db session cannot be None.")

    test_run_id = getattr(test_run, "id", None)
    logger.info(
        "Evaluation results processing starting: test_run_id=%s status=%s",
        test_run_id,
        test_run.status,
    )

    existing_results = (
        db.query(EvaluationResult)
        .filter(
            EvaluationResult.test_run_id == test_run.id
        )
        .all()
    )

    if existing_results:
        logger.info(
            "Evaluation results already exist: test_run_id=%s count=%d",
            test_run_id,
            len(existing_results),
        )
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

    if test_run.status == "failed":
        results.extend(
            [
                EvaluationResult(
                    test_run_id=test_run.id,
                    metric_name="correctness",
                    score=0.0,
                    status="failed",
                    explanation=(
                        test_run.error_message
                        or "Agent execution failed."
                    ),
                    configuration_version=1,
                    configuration={},
                ),
                EvaluationResult(
                    test_run_id=test_run.id,
                    metric_name="latency",
                    score=0.0,
                    status="failed",
                    explanation=(
                        "Latency could not be evaluated "
                        "because agent execution failed."
                    ),
                    configuration_version=1,
                    configuration={},
                ),
            ]
        )

    else:
        metric_execution_results = execute_metrics(
            test_case,
            test_run,
        )

        for metric_execution_result in metric_execution_results:
            metric_result = metric_execution_result.metric_result

            results.append(
                EvaluationResult(
                    test_run_id=test_run.id,
                    metric_name=metric_result.metric_name,
                    score=metric_result.score,
                    status=metric_result.status,
                    explanation=metric_result.explanation,
                    configuration_version=(
                        metric_execution_result.configuration_version
                    ),
                    configuration=(
                        metric_execution_result.configuration
                    ),
                )
            )

    db.add_all(results)
    try:
        db.commit()
        logger.info(
            "Evaluation results persisted successfully: test_run_id=%s result_count=%d",
            test_run_id,
            len(results),
        )
    except Exception as exc:
        db.rollback()
        logger.error(
            "Evaluation results database commit failed: test_run_id=%s error=%s",
            test_run_id,
            str(exc),
        )
        raise

    for result in results:
        db.refresh(result)

    return results