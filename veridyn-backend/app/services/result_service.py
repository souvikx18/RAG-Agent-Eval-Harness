from app.models.evaluation_result import EvaluationResult
from app.models.test_run import TestRun
from sqlalchemy.orm import Session


def create_evaluation_result(
    test_run: TestRun,
    db: Session,
) -> EvaluationResult:

    result = EvaluationResult(
        test_run_id=test_run.id,
        metric_name="basic_execution",
        score=1.0 if test_run.result == "passed" else 0.0,
        status="passed" if test_run.result == "passed" else "failed",
        explanation=(
            "Test run completed successfully."
            if test_run.result == "passed"
            else "Test run failed."
        ),
    )

    db.add(result)
    db.commit()
    db.refresh(result)

    return result