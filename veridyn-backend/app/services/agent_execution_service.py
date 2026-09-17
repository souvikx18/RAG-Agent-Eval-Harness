import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.test_run import TestRun
from app.models.test_case import TestCase


def execute_test_run(
    test_run: TestRun,
    db: Session,
) -> TestRun:
    start_time = time.perf_counter()

    try:
        test_case = (
            db.query(TestCase)
            .filter(TestCase.id == test_run.test_case_id)
            .first()
        )

        if not test_case:
            raise ValueError("Test case not found")

        test_run.status = "running"
        db.commit()

        # Temporary agent execution.
        # The real AI agent adapter will be connected later.
        actual_output = (
            f"Agent received input: {test_case.input_data}. "
            f"Expected behavior: {test_case.expected_behavior}"
        )

        latency_ms = int(
            (time.perf_counter() - start_time) * 1000
        )

        test_run.status = "completed"
        test_run.actual_output = actual_output
        test_run.result = "passed"
        test_run.latency_ms = latency_ms
        test_run.completed_at = datetime.now(timezone.utc)

    except Exception as exc:
        test_run.status = "failed"
        test_run.error_message = str(exc)
        test_run.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(test_run)

    return test_run