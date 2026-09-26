from sqlalchemy.orm import Session

from app.models.evaluation import Evaluation
from app.models.test_case import TestCase
from app.models.test_run import TestRun


def calculate_evaluation_statistics(
    evaluation: Evaluation,
    db: Session,
) -> dict:

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
