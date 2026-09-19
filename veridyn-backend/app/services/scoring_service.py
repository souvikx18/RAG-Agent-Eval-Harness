from sqlalchemy.orm import Session

from app.models.evaluation import Evaluation
from app.models.evaluation_result import EvaluationResult
from app.models.test_run import TestRun
from app.models.test_case import TestCase


def calculate_evaluation_score(
    evaluation: Evaluation,
    db: Session,
) -> float:

    results = (
        db.query(EvaluationResult)
        .join(
            TestRun,
            EvaluationResult.test_run_id == TestRun.id,
        )
        .join(
            TestCase,
            TestRun.test_case_id == TestCase.id,
        )
        .filter(
            TestCase.evaluation_id == evaluation.id
        )
        .all()
    )

    scores = [
        result.score
        for result in results
        if result.score is not None
    ]

    if not scores:
        return 0.0

    return sum(scores) / len(scores)