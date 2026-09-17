from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.evaluation import Evaluation
from app.models.test_case import TestCase
from app.services.test_run_service import start_test_run


def start_evaluation(
    evaluation: Evaluation,
    db: Session,
) -> Evaluation:
    evaluation.status = "running"
    evaluation.started_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(evaluation)

    test_cases = (
        db.query(TestCase)
        .filter(TestCase.evaluation_id == evaluation.id)
        .order_by(TestCase.created_at.asc())
        .all()
    )

    for test_case in test_cases:
        start_test_run(test_case, db)

    return evaluation


def complete_evaluation(
    evaluation: Evaluation,
    db: Session,
    summary: str | None = None,
) -> Evaluation:
    evaluation.status = "completed"
    evaluation.completed_at = datetime.now(timezone.utc)
    evaluation.summary = summary

    db.commit()
    db.refresh(evaluation)

    return evaluation