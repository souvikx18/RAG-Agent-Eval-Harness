import uuid
from app.models.evaluation_result import EvaluationResult
from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.services.result_service import create_evaluation_result
from app.services.metrics.registry import metric_registry


def test_create_evaluation_result_successful_run(db):
    metric_registry.reset()

    test_case = TestCase(
        id=uuid.uuid4(),
        evaluation_id=uuid.uuid4(),
        name="Result Service Success Test",
        category="functional",
        input_data="Hello",
        expected_behavior="helpful response",
        is_adversarial=False,
    )
    db.add(test_case)
    db.commit()

    test_run = TestRun(
        id=uuid.uuid4(),
        test_case_id=test_case.id,
        status="completed",
        actual_output="This is a helpful response.",
        latency_ms=300,
        result="passed",
    )
    db.add(test_run)
    db.commit()

    results = create_evaluation_result(test_run, db)

    assert len(results) == 2

    results_by_name = {
        result.metric_name: result
        for result in results
    }

    assert "correctness" in results_by_name
    assert "latency" in results_by_name

    correctness_result = results_by_name["correctness"]
    assert correctness_result.score == 1.0
    assert correctness_result.status == "passed"
    assert correctness_result.configuration_version == 1
    assert correctness_result.configuration == {
        "case_sensitive": False,
    }

    latency_result = results_by_name["latency"]
    assert latency_result.score == 1.0
    assert latency_result.status == "passed"
    assert latency_result.configuration_version == 1
    assert latency_result.configuration == {
        "fast_threshold_ms": 500,
        "acceptable_threshold_ms": 1000,
        "high_threshold_ms": 2000,
    }

    # Verify rows persisted in DB
    persisted = (
        db.query(EvaluationResult)
        .filter(EvaluationResult.test_run_id == test_run.id)
        .all()
    )
    assert len(persisted) == 2


def test_create_evaluation_result_failed_run(db):
    test_case = TestCase(
        id=uuid.uuid4(),
        evaluation_id=uuid.uuid4(),
        name="Result Service Failure Test",
        category="functional",
        input_data="Hello",
        expected_behavior="helpful response",
        is_adversarial=False,
    )
    db.add(test_case)
    db.commit()

    test_run = TestRun(
        id=uuid.uuid4(),
        test_case_id=test_case.id,
        status="failed",
        error_message="Agent timed out.",
        result="failed",
    )
    db.add(test_run)
    db.commit()

    results = create_evaluation_result(test_run, db)

    assert len(results) == 2

    for result in results:
        assert result.score == 0.0
        assert result.status == "failed"
        assert result.configuration_version == 1
        assert result.configuration == {}


def test_create_evaluation_result_reflects_metric_configuration(db):
    metric_registry.reset()

    try:
        metric_registry.configure(
            "correctness",
            {"case_sensitive": True},
        )

        test_case = TestCase(
            id=uuid.uuid4(),
            evaluation_id=uuid.uuid4(),
            name="Configured Metric Test",
            category="functional",
            input_data="Hello",
            expected_behavior="Target",
            is_adversarial=False,
        )
        db.add(test_case)
        db.commit()

        test_run = TestRun(
            id=uuid.uuid4(),
            test_case_id=test_case.id,
            status="completed",
            actual_output="target",
            latency_ms=100,
            result="failed",
        )
        db.add(test_run)
        db.commit()

        results = create_evaluation_result(test_run, db)

        correctness_result = next(
            r for r in results if r.metric_name == "correctness"
        )
        assert correctness_result.configuration_version == 2
        assert correctness_result.configuration == {
            "case_sensitive": True,
        }
        assert correctness_result.score == 0.0

    finally:
        metric_registry.reset()
