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


def test_evaluation_statistics_with_no_runs(db):
    evaluation = Evaluation(
        agent_version_id=uuid.uuid4(),
        status="completed",
        trigger_type="manual",
    )

    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)

    statistics = calculate_evaluation_statistics(
        evaluation,
        db,
    )

    assert statistics["total_runs"] == 0
    assert statistics["passed_runs"] == 0
    assert statistics["failed_runs"] == 0
    assert statistics["average_latency_ms"] == 0.0


def test_evaluation_statistics_with_failed_runs(db):
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
        name="Failed Statistics Test",
        category="reliability",
        input_data="Hello",
        expected_behavior="Successful response",
        is_adversarial=False,
    )

    db.add(test_case)
    db.commit()
    db.refresh(test_case)

    run_one = TestRun(
        test_case_id=test_case.id,
        status="failed",
        result="failed",
        latency_ms=200,
    )

    run_two = TestRun(
        test_case_id=test_case.id,
        status="failed",
        result="failed",
        latency_ms=400,
    )

    db.add_all([run_one, run_two])
    db.commit()

    statistics = calculate_evaluation_statistics(
        evaluation,
        db,
    )

    assert statistics["total_runs"] == 2
    assert statistics["passed_runs"] == 0
    assert statistics["failed_runs"] == 2
    assert statistics["average_latency_ms"] == 300.0


def test_evaluation_statistics_with_missing_latency(db):
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
        name="Missing Latency Test",
        category="performance",
        input_data="Hello",
        expected_behavior="Successful response",
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
        status="completed",
        result="passed",
        latency_ms=None,
    )

    db.add_all([run_one, run_two])
    db.commit()

    statistics = calculate_evaluation_statistics(
        evaluation,
        db,
    )

    assert statistics["total_runs"] == 2
    assert statistics["passed_runs"] == 2
    assert statistics["failed_runs"] == 0
    assert statistics["average_latency_ms"] == 100.0


def test_evaluation_statistics_with_multiple_test_cases(db):
    evaluation = Evaluation(
        agent_version_id=uuid.uuid4(),
        status="completed",
        trigger_type="manual",
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)

    test_case_one = TestCase(
        evaluation_id=evaluation.id,
        name="Test Case One",
        category="functional",
        input_data="Hello",
        expected_behavior="Successful response",
        is_adversarial=False,
    )

    test_case_two = TestCase(
        evaluation_id=evaluation.id,
        name="Test Case Two",
        category="reliability",
        input_data="Weather",
        expected_behavior="Weather response",
        is_adversarial=False,
    )

    db.add_all([test_case_one, test_case_two])
    db.commit()
    db.refresh(test_case_one)
    db.refresh(test_case_two)

    run_one = TestRun(
        test_case_id=test_case_one.id,
        status="completed",
        result="passed",
        latency_ms=100,
    )

    run_two = TestRun(
        test_case_id=test_case_two.id,
        status="completed",
        result="passed",
        latency_ms=200,
    )

    run_three = TestRun(
        test_case_id=test_case_two.id,
        status="failed",
        result="failed",
        latency_ms=300,
    )

    db.add_all([run_one, run_two, run_three])
    db.commit()

    statistics = calculate_evaluation_statistics(evaluation, db)

    assert statistics["total_runs"] == 3
    assert statistics["passed_runs"] == 2
    assert statistics["failed_runs"] == 1
    assert statistics["average_latency_ms"] == 200.0

