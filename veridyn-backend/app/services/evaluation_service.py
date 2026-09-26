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

    return evaluation


def calculate_evaluation_statistics(
    test_runs: list[TestRun],
) -> dict:

    total_runs = len(test_runs)

    passed_runs = sum(
        1
        for test_run in test_runs
        if test_run.status == "completed"
        and test_run.result == "passed"
    )

    failed_runs = sum(
        1
        for test_run in test_runs
        if test_run.status == "failed"
        or test_run.result == "failed"
    )

    latency_values = [
        test_run.latency_ms
        for test_run in test_runs
        if test_run.latency_ms is not None
    ]

    average_latency_ms = (
        sum(latency_values) / len(latency_values)
        if latency_values
        else 0.0
    )

    return {
        "total_runs": total_runs,
        "passed_runs": passed_runs,
        "failed_runs": failed_runs,
        "average_latency_ms": round(
            average_latency_ms,
            2,
        ),
    }


def build_evaluation_summary(
    overall_score: float,
    test_runs: list[TestRun],
) -> str:

    statistics = calculate_evaluation_statistics(
        test_runs
    )

    return (
        f"Evaluation completed with overall score: "
        f"{overall_score:.2f}. "
        f"Total test runs: "
        f"{statistics['total_runs']}. "
        f"Passed: "
        f"{statistics['passed_runs']}. "
        f"Failed: "
        f"{statistics['failed_runs']}. "
        f"Average latency: "
        f"{statistics['average_latency_ms']:.2f} ms."
    )


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

    evaluation.overall_score = overall_score
    evaluation.status = "completed"
    evaluation.completed_at = datetime.now(timezone.utc)
    evaluation.summary = (
        summary
        or build_evaluation_summary(
            overall_score,
            test_runs,
        )
    )

    db.commit()
    db.refresh(evaluation)

    create_deployment_gate(
        evaluation,
        db,
    )

    return evaluation