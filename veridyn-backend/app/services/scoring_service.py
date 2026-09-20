from sqlalchemy.orm import Session

from app.models.evaluation import Evaluation
from app.models.evaluation_result import EvaluationResult
from app.models.test_run import TestRun
from app.models.test_case import TestCase


METRIC_WEIGHTS = {
    "correctness": 0.70,
    "latency": 0.30,
}


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

    if not results:
        return 0.0

    weighted_score = 0.0
    total_weight = 0.0

    for result in results:
        if result.score is None:
            continue

        weight = METRIC_WEIGHTS.get(
            result.metric_name,
            0.0,
        )

        if weight == 0.0:
            continue

        weighted_score += result.score * weight
        total_weight += weight

    if total_weight == 0.0:
        return 0.0

    return weighted_score / total_weight