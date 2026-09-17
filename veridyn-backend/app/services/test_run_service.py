from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.test_case import TestCase
from app.models.test_run import TestRun


def start_test_run(
    test_case: TestCase,
    db: Session,
) -> TestRun:
    test_run = TestRun(
        test_case_id=test_case.id,
        status="running",
        started_at=datetime.now(timezone.utc),
    )

    db.add(test_run)
    db.commit()
    db.refresh(test_run)

    return test_run


def complete_test_run(
    test_run: TestRun,
    db: Session,
    actual_output: str | None = None,
    result: str | None = None,
    error_message: str | None = None,
    latency_ms: int | None = None,
) -> TestRun:
    test_run.status = "completed"
    test_run.actual_output = actual_output
    test_run.result = result
    test_run.error_message = error_message
    test_run.latency_ms = latency_ms
    test_run.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(test_run)

    return test_run