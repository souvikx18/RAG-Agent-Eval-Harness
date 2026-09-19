from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.evaluation_result import EvaluationResult
from app.models.test_run import TestRun


def create_evaluation_result(
    test_run: TestRun,
    db: Session,
) -> EvaluationResult:

    if test_run.status not in ["completed", "failed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test run has not finished",
        )

    if test_run.status == "completed" and not test_run.actual_output:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Completed test run has no actual output",
        )

    if test_run.status == "failed":
        score = 0.0
        result_status = "failed"
        explanation = (
            test_run.error_message
            or "Test run failed."
        )
    else:
        score = 1.0
        result_status = "passed"
        explanation = "Test run completed successfully."

    result = EvaluationResult(
        test_run_id=test_run.id,
        metric_name="basic_execution",
        score=score,
        status=result_status,
        explanation=explanation,
    )

    db.add(result)
    db.commit()
    db.refresh(result)

    return result