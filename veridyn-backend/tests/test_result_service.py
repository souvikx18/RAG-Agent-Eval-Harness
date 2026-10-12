import uuid
import pytest
from app.models.evaluation_result import EvaluationResult
from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.services.metric_execution_service import execute_metrics
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


def test_metric_configuration_audit(db):
    """
    Audit invariant:
    The configuration persisted in EvaluationResult must exactly match the
    configuration captured by MetricExecutionResult across the complete path:
    Metric -> MetricExecutionResult -> result_service -> EvaluationResult.
    """
    metric_registry.reset()

    try:
        # Configure metric: version increments to 2
        metric_registry.configure(
            "correctness",
            {"case_sensitive": True},
        )

        test_case = TestCase(
            id=uuid.uuid4(),
            evaluation_id=uuid.uuid4(),
            name="Audit Invariant Test Case",
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
            latency_ms=120,
            result="passed",
        )
        db.add(test_run)
        db.commit()

        # Step 1: Capture execution results directly from execute_metrics
        execution_results = execute_metrics(test_case, test_run)
        correctness_execution = next(
            r for r in execution_results if r.metric_result.metric_name == "correctness"
        )

        # Verify the metric execution result captured version 2 and configuration
        assert correctness_execution.configuration_version == 2
        assert correctness_execution.configuration == {
            "case_sensitive": True,
        }

        # Step 2: Persist evaluation results through result_service
        persisted_results = create_evaluation_result(test_run, db)
        persisted_correctness = next(
            r for r in persisted_results if r.metric_name == "correctness"
        )

        # Step 3: Reload persisted result from database
        persisted_record = (
            db.query(EvaluationResult)
            .filter(EvaluationResult.id == persisted_correctness.id)
            .first()
        )
        assert persisted_record is not None

        # Step 4: Verify persisted result exactly matches MetricExecutionResult
        assert (
            persisted_record.configuration_version
            == correctness_execution.configuration_version
        )
        assert (
            persisted_record.configuration
            == correctness_execution.configuration
        )
        assert persisted_record.configuration_version == 2
        assert persisted_record.configuration == {
            "case_sensitive": True,
        }

        # Step 5: Verify decoupling from future registry changes
        # Reconfiguring or mutating registry must not alter persisted result
        metric_registry.configure(
            "correctness",
            {"case_sensitive": False},
        )
        db.refresh(persisted_record)
        assert persisted_record.configuration_version == 2
        assert persisted_record.configuration == {
            "case_sensitive": True,
        }

    finally:
        metric_registry.reset()


def test_metric_evaluation_service_end_to_end_pipeline(db):
    """
    Step 182: Metric Evaluation Service End-to-End Integration Tests.
    - Validates the complete pipeline:
      Registry -> MetricExecutionService -> Metric.evaluate() -> ResultService -> DB persistence.
    - Tests successful metric evaluation with correct scoring and status calculation.
    - Verifies association with the target TestRun ID and test case context.
    - Tests evaluation failures (metric exception handling without falsely claiming success).
    - Tests unknown metric rejection using the existing registry contract.
    - Verifies snapshot immutability: live registry changes after evaluation do not mutate stored snapshots.
    """
    from unittest.mock import patch
    from app.services.metrics.base_metric import Metric, MetricContext, MetricResult

    metric_registry.reset()

    try:
        # 1. Setup entities in DB
        test_case = TestCase(
            id=uuid.uuid4(),
            evaluation_id=uuid.uuid4(),
            name="E2E Metric Test Case",
            category="functional",
            input_data="What is the capital of France?",
            expected_behavior="Paris is the capital of France",
            is_adversarial=False,
        )
        db.add(test_case)
        db.commit()

        test_run = TestRun(
            id=uuid.uuid4(),
            test_case_id=test_case.id,
            status="completed",
            actual_output="Paris is the capital of France.",
            latency_ms=250,
            result="passed",
            executor_type="PlaceholderAgentExecutor",
        )
        db.add(test_run)
        db.commit()

        # 2. Pipeline Execution: execute_metrics -> create_evaluation_result
        persisted_results = create_evaluation_result(test_run, db)
        assert len(persisted_results) == 2

        results_by_metric = {r.metric_name: r for r in persisted_results}
        assert "correctness" in results_by_metric
        assert "latency" in results_by_metric

        # Validate correctness
        corr = results_by_metric["correctness"]
        assert corr.test_run_id == test_run.id
        assert corr.score == 1.0
        assert corr.status == "passed"
        assert corr.explanation == "Expected behavior was found in the actual output."
        assert corr.configuration_version == 1
        assert corr.configuration == {"case_sensitive": False}

        # Validate latency
        lat = results_by_metric["latency"]
        assert lat.test_run_id == test_run.id
        assert lat.score == 1.0
        assert lat.status == "passed"
        assert lat.explanation == "Latency is within the target range."
        assert lat.configuration_version == 1
        assert lat.configuration == {
            "fast_threshold_ms": 500,
            "acceptable_threshold_ms": 1000,
            "high_threshold_ms": 2000,
        }

        # 3. Test evaluation failures (simulated metric exception)
        # Register a custom failing metric
        class CrashingMetric(Metric):
            @property
            def name(self) -> str:
                return "crashing_metric"

            def evaluate(self, context: MetricContext) -> MetricResult:
                raise RuntimeError("Internal metric compute failure")

        metric_registry.register(CrashingMetric())

        test_run_fail = TestRun(
            id=uuid.uuid4(),
            test_case_id=test_case.id,
            status="completed",
            actual_output="Paris is the capital of France.",
            latency_ms=250,
            result="passed",
            executor_type="PlaceholderAgentExecutor",
        )
        db.add(test_run_fail)
        db.commit()

        results_with_crash = create_evaluation_result(test_run_fail, db)
        crash_res = next(r for r in results_with_crash if r.metric_name == "crashing_metric")
        assert crash_res.status == "failed"
        assert crash_res.score == 0.0
        assert "Metric execution failed: Internal metric compute failure" in crash_res.explanation

        # 4. Test unknown metric rejection in registry contract
        with pytest.raises(ValueError) as exc_info:
            metric_registry.get("non_existent_metric")
        assert "Unknown metric: non_existent_metric" in str(exc_info.value)

        # 5. Snapshot immutability verification: live registry configuration change does not alter persisted result
        metric_registry.configure("correctness", {"case_sensitive": True})
        db.refresh(corr)
        assert corr.configuration_version == 1
        assert corr.configuration == {"case_sensitive": False}

        # Clean up created records
        db.query(EvaluationResult).filter(
            EvaluationResult.test_run_id.in_([test_run.id, test_run_fail.id])
        ).delete(synchronize_session=False)
        db.query(TestRun).filter(
            TestRun.id.in_([test_run.id, test_run_fail.id])
        ).delete(synchronize_session=False)
        db.query(TestCase).filter(TestCase.id == test_case.id).delete(synchronize_session=False)
        db.commit()

    finally:
        metric_registry.reset()






