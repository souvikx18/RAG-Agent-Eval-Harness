import uuid

from app.models.evaluation import Evaluation
from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.services.evaluation_statistics_service import (
    calculate_evaluation_statistics,
)


def test_calculate_evaluation_statistics(db):
    evaluation = Evaluation(
        agent_version_id=uuid.uuid4(),
        status="completed",
        trigger_type="manual",
    )

    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)

    test_case = TestCase(
        evaluation_id=evaluation.id,
        name="Statistics Test",
        category="functional",
        input_data="Hello",
        expected_behavior="Helpful greeting",
        is_adversarial=False,
    )

    db.add(test_case)
    db.commit()
    db.refresh(test_case)

    run_one = TestRun(
        test_case_id=test_case.id,
        status="completed",
        result="passed",
        latency_ms=100,
    )

    run_two = TestRun(
        test_case_id=test_case.id,
        status="failed",
        result="failed",
        latency_ms=300,
    )

    db.add_all([run_one, run_two])
    db.commit()

    statistics = calculate_evaluation_statistics(
        evaluation,
        db,
    )

    assert statistics["total_runs"] == 2
    assert statistics["passed_runs"] == 1
    assert statistics["failed_runs"] == 1
    assert statistics["average_latency_ms"] == 200.0
