from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.test_run import TestRun
from app.models.evaluation import Evaluation
from app.models.test_case import TestCase
from app.services.test_run_service import start_test_run
from app.services.scoring_service import calculate_evaluation_score
from app.services.deployment_gate_service import create_deployment_gate


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

    test_runs = (
        db.query(TestRun)
        .join(
            TestCase,
            TestRun.test_case_id == TestCase.id,
        )
        .filter(
            TestCase.evaluation_id == evaluation.id
        )
        .all()
    )

    if not test_runs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Evaluation has no test runs",
        )

    incomplete_runs = [
        test_run
        for test_run in test_runs
        if test_run.status not in ["completed", "failed"]
    ]

    if incomplete_runs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Evaluation has unfinished test runs",
        )

    overall_score = calculate_evaluation_score(
        evaluation,
        db,
    )

    create_deployment_gate(
        evaluation,
        overall_score,
        db,
    )

    evaluation.status = "completed"
    evaluation.completed_at = datetime.now(timezone.utc)
    evaluation.summary = (
        summary
        or f"Evaluation completed with overall score: "
        f"{overall_score:.2f}"
    )

    db.commit()
    db.refresh(evaluation)

    return evaluation