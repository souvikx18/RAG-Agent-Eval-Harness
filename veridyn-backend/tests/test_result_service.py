import uuid
import pytest
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


def test_metric_configuration_persistence_verification(db):
    metric_registry.reset()

    try:
        metric_registry.configure(
            "correctness",
            {"case_sensitive": True},
        )

        test_case = TestCase(
            id=uuid.uuid4(),
            evaluation_id=uuid.uuid4(),
            name="Persistence Verification Case",
            category="functional",
            input_data="Sample input",
            expected_behavior="Sample output",
            is_adversarial=False,
        )
        db.add(test_case)
        db.commit()

        test_run = TestRun(
            id=uuid.uuid4(),
            test_case_id=test_case.id,
            status="completed",
            actual_output="Sample output",
            latency_ms=150,
            result="passed",
        )
        db.add(test_run)
        db.commit()

        create_evaluation_result(test_run, db)

        persisted_results = (
            db.query(EvaluationResult)
            .filter(EvaluationResult.test_run_id == test_run.id)
            .all()
        )

        correctness_result = next(
            r for r in persisted_results if r.metric_name == "correctness"
        )

        assert correctness_result.configuration_version == 2
        assert correctness_result.configuration == {
            "case_sensitive": True,
        }

    finally:
        metric_registry.reset()


def test_evaluation_result_configuration_version_model_validation(db):
    table = EvaluationResult.__table__

    assert table.c.configuration_version.nullable is False
    assert table.c.configuration_version.default.arg == 1

    test_case = TestCase(
        id=uuid.uuid4(),
        evaluation_id=uuid.uuid4(),
        name="Validation Model Case",
        category="functional",
        input_data="Sample",
        expected_behavior="Sample",
        is_adversarial=False,
    )
    db.add(test_case)
    db.commit()

    test_run = TestRun(
        id=uuid.uuid4(),
        test_case_id=test_case.id,
        status="completed",
        result="passed",
    )
    db.add(test_run)
    db.commit()

    # Verify invalid versions (0 and negative) are rejected at model boundary
    with pytest.raises(ValueError, match="Configuration version must be at least 1"):
        EvaluationResult(
            test_run_id=test_run.id,
            metric_name="correctness",
            score=1.0,
            status="passed",
            configuration_version=0,
            configuration={},
        )

    with pytest.raises(ValueError, match="Configuration version must be at least 1"):
        EvaluationResult(
            test_run_id=test_run.id,
            metric_name="correctness",
            score=1.0,
            status="passed",
            configuration_version=-1,
            configuration={},
        )

    # Verify valid version (1) persists and retrieves successfully
    valid_result = EvaluationResult(
        test_run_id=test_run.id,
        metric_name="correctness",
        score=1.0,
        status="passed",
        configuration_version=1,
        configuration={},
    )
    db.add(valid_result)
    db.commit()

    retrieved = (
        db.query(EvaluationResult)
        .filter(EvaluationResult.id == valid_result.id)
        .first()
    )
    assert retrieved is not None
    assert retrieved.configuration_version == 1

    # Verify mutating existing instance to invalid version is rejected
    with pytest.raises(ValueError, match="Configuration version must be at least 1"):
        retrieved.configuration_version = 0

    with pytest.raises(ValueError, match="Configuration version must be at least 1"):
        retrieved.configuration_version = -1


def test_evaluation_result_nested_json_configuration_persistence(db):
    test_case = TestCase(
        id=uuid.uuid4(),
        evaluation_id=uuid.uuid4(),
        name="JSON Configuration Persistence Test",
        category="functional",
        input_data="Nested JSON input",
        expected_behavior="Nested JSON output",
        is_adversarial=False,
    )
    db.add(test_case)
    db.commit()

    test_run = TestRun(
        id=uuid.uuid4(),
        test_case_id=test_case.id,
        status="completed",
        result="passed",
    )
    db.add(test_run)
    db.commit()

    nested_config = {
        "case_sensitive": True,
        "options": {
            "trim_whitespace": True,
            "normalize_case": False,
        },
    }

    result = EvaluationResult(
        test_run_id=test_run.id,
        metric_name="correctness",
        score=1.0,
        status="passed",
        configuration_version=2,
        configuration=nested_config,
    )
    db.add(result)
    db.commit()

    persisted_result = (
        db.query(EvaluationResult)
        .filter(EvaluationResult.id == result.id)
        .first()
    )

    assert persisted_result is not None
    assert persisted_result.configuration == {
        "case_sensitive": True,
        "options": {
            "trim_whitespace": True,
            "normalize_case": False,
        },
    }
    assert isinstance(persisted_result.configuration["options"]["trim_whitespace"], bool)
    assert persisted_result.configuration["options"]["trim_whitespace"] is True
    assert isinstance(persisted_result.configuration["options"]["normalize_case"], bool)
    assert persisted_result.configuration["options"]["normalize_case"] is False


def test_evaluation_result_configuration_type_safety(db):
    test_case = TestCase(
        id=uuid.uuid4(),
        evaluation_id=uuid.uuid4(),
        name="Configuration Type Safety Test",
        category="functional",
        input_data="Sample input",
        expected_behavior="Sample output",
        is_adversarial=False,
    )
    db.add(test_case)
    db.commit()

    test_run = TestRun(
        id=uuid.uuid4(),
        test_case_id=test_case.id,
        status="completed",
        result="passed",
    )
    db.add(test_run)
    db.commit()

    # 1. Empty dict accepted
    empty_result = EvaluationResult(
        test_run_id=test_run.id,
        metric_name="correctness",
        score=1.0,
        status="passed",
        configuration_version=1,
        configuration={},
    )
    db.add(empty_result)
    db.commit()

    persisted_empty = (
        db.query(EvaluationResult)
        .filter(EvaluationResult.id == empty_result.id)
        .first()
    )
    assert persisted_empty is not None
    assert persisted_empty.configuration == {}

    # 2. Normal configuration dict accepted
    normal_result = EvaluationResult(
        test_run_id=test_run.id,
        metric_name="correctness",
        score=1.0,
        status="passed",
        configuration_version=1,
        configuration={
            "case_sensitive": True,
        },
    )
    db.add(normal_result)
    db.commit()

    persisted_normal = (
        db.query(EvaluationResult)
        .filter(EvaluationResult.id == normal_result.id)
        .first()
    )
    assert persisted_normal is not None
    assert persisted_normal.configuration == {
        "case_sensitive": True,
    }

    # 3. None rejected
    with pytest.raises((ValueError, TypeError)):
        EvaluationResult(
            test_run_id=test_run.id,
            metric_name="correctness",
            score=1.0,
            status="passed",
            configuration_version=1,
            configuration=None,
        )

    # 4. Non-dictionary value rejected (e.g. string "invalid")
    with pytest.raises((ValueError, TypeError)):
        EvaluationResult(
            test_run_id=test_run.id,
            metric_name="correctness",
            score=1.0,
            status="passed",
            configuration_version=1,
            configuration="invalid",
        )

    # Also verify non-dict types like lists are rejected
    with pytest.raises((ValueError, TypeError)):
        EvaluationResult(
            test_run_id=test_run.id,
            metric_name="correctness",
            score=1.0,
            status="passed",
            configuration_version=1,
            configuration=[1, 2, 3],
        )

    # Also verify mutating existing persisted instance to invalid configuration is rejected
    with pytest.raises((ValueError, TypeError)):
        persisted_normal.configuration = None

    with pytest.raises((ValueError, TypeError)):
        persisted_normal.configuration = "invalid"




