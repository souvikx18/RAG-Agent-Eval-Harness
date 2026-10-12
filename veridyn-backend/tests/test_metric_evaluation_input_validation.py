import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.evaluation_result import EvaluationResult, ConfigurationValidationError
from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.services.metric_execution_service import (
    execute_metrics,
    execute_metrics_as_dicts,
)
from app.services.metrics.base_metric import (
    Metric,
    MetricContext,
    MetricExecutionResult,
    MetricResult,
)
from app.services.metrics.correctness_metric import CorrectnessMetric
from app.services.metrics.latency_metric import LatencyMetric
from app.services.metrics.registry import MetricRegistry, metric_registry
from app.services.result_service import create_evaluation_result


# ---------------------------------------------------------------------------
# 1. Metric Input Validation Tests
# ---------------------------------------------------------------------------

def test_correctness_metric_input_validation_missing_and_whitespace():
    """Verify CorrectnessMetric handles missing, empty, and whitespace strings."""
    metric = CorrectnessMetric()

    # None actual_output -> failed (no output produced)
    res_none_output = metric.evaluate(MetricContext(expected_behavior="hello", actual_output=None, latency_ms=100))
    assert res_none_output.score == 0.0
    assert res_none_output.status == "failed"
    assert "No actual output was produced" in res_none_output.explanation

    # Empty actual_output -> failed
    res_empty_output = metric.evaluate(MetricContext(expected_behavior="hello", actual_output="", latency_ms=100))
    assert res_empty_output.score == 0.0
    assert res_empty_output.status == "failed"

    # Whitespace actual_output -> failed
    res_ws_output = metric.evaluate(MetricContext(expected_behavior="hello", actual_output="   ", latency_ms=100))
    assert res_ws_output.score == 0.0
    assert res_ws_output.status == "failed"

    # None expected_behavior -> passed (no expectation provided)
    res_none_expected = metric.evaluate(MetricContext(expected_behavior=None, actual_output="hello", latency_ms=100))
    assert res_none_expected.score == 1.0
    assert res_none_expected.status == "passed"
    assert "No expected behavior was provided" in res_none_expected.explanation

    # Empty expected_behavior -> passed
    res_empty_expected = metric.evaluate(MetricContext(expected_behavior="", actual_output="hello", latency_ms=100))
    assert res_empty_expected.score == 1.0
    assert res_empty_expected.status == "passed"

    # Whitespace expected_behavior -> passed
    res_ws_expected = metric.evaluate(MetricContext(expected_behavior="   ", actual_output="hello", latency_ms=100))
    assert res_ws_expected.score == 1.0
    assert res_ws_expected.status == "passed"


def test_correctness_metric_input_validation_invalid_types():
    """Verify CorrectnessMetric rejects non-string inputs safely without unhandled crashes."""
    metric = CorrectnessMetric()

    # Integer actual_output -> fails safely
    res_int_output = metric.evaluate(MetricContext(expected_behavior="hello", actual_output=123, latency_ms=100))
    assert res_int_output.score == 0.0
    assert res_int_output.status == "failed"
    assert "must be strings" in res_int_output.explanation

    # Dict actual_output -> fails safely
    res_dict_output = metric.evaluate(MetricContext(expected_behavior="hello", actual_output={"data": 1}, latency_ms=100))
    assert res_dict_output.score == 0.0
    assert res_dict_output.status == "failed"

    # List expected_behavior -> fails safely
    res_list_expected = metric.evaluate(MetricContext(expected_behavior=["expected"], actual_output="hello", latency_ms=100))
    assert res_list_expected.score == 0.0
    assert res_list_expected.status == "failed"
    assert "must be strings" in res_list_expected.explanation


def test_latency_metric_input_validation_boundary_values():
    """Verify LatencyMetric boundaries and negative latency handling."""
    metric = LatencyMetric()
    metric.configure({"fast_threshold_ms": 500, "acceptable_threshold_ms": 1000, "high_threshold_ms": 2000})

    # Exact fast threshold
    res_fast = metric.evaluate(MetricContext(expected_behavior=None, actual_output="ok", latency_ms=500))
    assert res_fast.score == 1.0
    assert res_fast.status == "passed"

    # 1 ms above fast threshold -> acceptable
    res_above_fast = metric.evaluate(MetricContext(expected_behavior=None, actual_output="ok", latency_ms=501))
    assert res_above_fast.score == 0.75
    assert res_above_fast.status == "passed"

    # Exact acceptable threshold
    res_acc = metric.evaluate(MetricContext(expected_behavior=None, actual_output="ok", latency_ms=1000))
    assert res_acc.score == 0.75
    assert res_acc.status == "passed"

    # 1 ms above acceptable -> high (failed)
    res_above_acc = metric.evaluate(MetricContext(expected_behavior=None, actual_output="ok", latency_ms=1001))
    assert res_above_acc.score == 0.5
    assert res_above_acc.status == "failed"

    # Exact high threshold
    res_high = metric.evaluate(MetricContext(expected_behavior=None, actual_output="ok", latency_ms=2000))
    assert res_high.score == 0.5
    assert res_high.status == "failed"

    # 1 ms above high threshold -> 0.0
    res_above_high = metric.evaluate(MetricContext(expected_behavior=None, actual_output="ok", latency_ms=2001))
    assert res_above_high.score == 0.0
    assert res_above_high.status == "failed"

    # Zero latency -> 1.0 (valid boundary)
    res_zero = metric.evaluate(MetricContext(expected_behavior=None, actual_output="ok", latency_ms=0))
    assert res_zero.score == 1.0
    assert res_zero.status == "passed"

    # Negative latency -> must fail safely (never produce misleading passing score)
    res_neg = metric.evaluate(MetricContext(expected_behavior=None, actual_output="ok", latency_ms=-1))
    assert res_neg.score == 0.0
    assert res_neg.status == "failed"
    assert "Latency cannot be negative" in res_neg.explanation

    res_neg_large = metric.evaluate(MetricContext(expected_behavior=None, actual_output="ok", latency_ms=-500))
    assert res_neg_large.score == 0.0
    assert res_neg_large.status == "failed"


def test_latency_metric_input_validation_invalid_types():
    """Verify LatencyMetric rejects invalid non-numeric types and booleans."""
    metric = LatencyMetric()

    # None latency -> fails safely
    res_none = metric.evaluate(MetricContext(expected_behavior=None, actual_output="ok", latency_ms=None))
    assert res_none.score == 0.0
    assert res_none.status == "failed"
    assert "Latency was not recorded" in res_none.explanation

    # String latency -> fails safely
    res_str = metric.evaluate(MetricContext(expected_behavior=None, actual_output="ok", latency_ms="500ms"))
    assert res_str.score == 0.0
    assert res_str.status == "failed"
    assert "Latency must be an integer" in res_str.explanation

    # Boolean latency (True/False) -> fails safely, preventing Python bool-as-int leakage
    res_bool = metric.evaluate(MetricContext(expected_behavior=None, actual_output="ok", latency_ms=True))
    assert res_bool.score == 0.0
    assert res_bool.status == "failed"
    assert "Latency must be an integer" in res_bool.explanation


# ---------------------------------------------------------------------------
# 2. Metric Configuration Safety Tests
# ---------------------------------------------------------------------------

def test_metric_registry_unsupported_metric_name_error_contract():
    """Verify unsupported metric names are rejected through established ValueError contract."""
    registry = MetricRegistry()

    with pytest.raises(ValueError, match="Unknown metric: non_existent"):
        registry.get("non_existent")

    with pytest.raises(ValueError, match="Unknown metric: unknown_metric"):
        registry.configure("unknown_metric", {"any": 1})


def test_metric_configuration_safety_and_immutability_on_failure():
    """Verify failed configuration does not mutate metric state, version, or registry snapshot."""
    registry = MetricRegistry()
    initial_snapshot = registry.get_configuration_snapshot()

    # 1. Invalid configuration types
    for invalid_config in [None, "invalid", [1, 2, 3]]:
        with pytest.raises(TypeError, match="Metric configuration must be a dictionary"):
            registry.configure("latency", invalid_config)
    assert registry.get_configuration_snapshot() == initial_snapshot

    # 2. Unknown configuration keys
    with pytest.raises(ValueError, match="Unknown latency configuration keys"):
        registry.configure("latency", {"unsupported_key": 100})
    assert registry.get_configuration_snapshot() == initial_snapshot

    with pytest.raises(ValueError, match="Unknown correctness configuration keys"):
        registry.configure("correctness", {"bogus": True})
    assert registry.get_configuration_snapshot() == initial_snapshot

    # 3. Invalid value types
    with pytest.raises(ValueError, match="case_sensitive must be a boolean"):
        registry.configure("correctness", {"case_sensitive": "true"})
    assert registry.get_configuration_snapshot() == initial_snapshot

    with pytest.raises(ValueError, match="fast_threshold_ms must be an integer"):
        registry.configure("latency", {"fast_threshold_ms": "fast"})
    assert registry.get_configuration_snapshot() == initial_snapshot

    with pytest.raises(ValueError, match="fast_threshold_ms must be an integer"):
        registry.configure("latency", {"fast_threshold_ms": True})
    assert registry.get_configuration_snapshot() == initial_snapshot

    # 4. Negative thresholds and inverted ordering
    with pytest.raises(ValueError, match="fast_threshold_ms cannot be negative"):
        registry.configure("latency", {"fast_threshold_ms": -10})
    assert registry.get_configuration_snapshot() == initial_snapshot

    with pytest.raises(ValueError, match="acceptable_threshold_ms must be greater than fast_threshold_ms"):
        registry.configure("latency", {"fast_threshold_ms": 1000, "acceptable_threshold_ms": 500})
    assert registry.get_configuration_snapshot() == initial_snapshot

    with pytest.raises(ValueError, match="high_threshold_ms must be greater than acceptable_threshold_ms"):
        registry.configure("latency", {"acceptable_threshold_ms": 1500, "high_threshold_ms": 1200})
    assert registry.get_configuration_snapshot() == initial_snapshot

    # Verify versions remained unchanged (version 1)
    assert registry.get("latency").get_configuration_version() == 1
    assert registry.get("correctness").get_configuration_version() == 1


# ---------------------------------------------------------------------------
# 3. Base Metric & Custom Metric Validation Tests
# ---------------------------------------------------------------------------

def test_metric_result_strict_validation():
    """Verify MetricResult enforces strict validation on score, status, name, and explanation."""
    # Boolean score must be rejected
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        MetricResult(metric_name="test", score=True, status="passed", explanation="valid")

    # Score out of bounds
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        MetricResult(metric_name="test", score=1.01, status="passed", explanation="valid")

    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        MetricResult(metric_name="test", score=-0.01, status="passed", explanation="valid")

    # Non-string metric_name or empty
    with pytest.raises(ValueError, match="Metric name cannot be empty"):
        MetricResult(metric_name="   ", score=1.0, status="passed", explanation="valid")

    # Status must be passed or failed
    with pytest.raises(ValueError, match="Metric status must be 'passed' or 'failed'"):
        MetricResult(metric_name="test", score=1.0, status="error", explanation="valid")

    # Non-string explanation or empty
    with pytest.raises(ValueError, match="Metric explanation cannot be empty"):
        MetricResult(metric_name="test", score=1.0, status="passed", explanation="   ")


def test_custom_metric_validation_and_safe_execution_handling():
    """Verify custom metric with strict domain validation executes safely inside service."""
    class StrictCustomMetric(Metric):
        def __init__(self):
            super().__init__()
            self.max_tokens = 50

        @property
        def name(self) -> str:
            return "strict_tokens"

        def configure(self, config: dict):
            if "max_tokens" not in config:
                raise ValueError("max_tokens is required.")
            if not isinstance(config["max_tokens"], int) or config["max_tokens"] <= 0:
                raise ValueError("max_tokens must be a positive integer.")
            self.max_tokens = config["max_tokens"]
            self._increment_configuration_version()

        def get_configuration(self) -> dict:
            return {"max_tokens": self.max_tokens}

        def evaluate(self, context: MetricContext) -> MetricResult:
            if not context.actual_output:
                return MetricResult(self.name, 0.0, "failed", "Output missing.")
            tokens = len(context.actual_output.split())
            if tokens > self.max_tokens:
                return MetricResult(self.name, 0.0, "failed", f"Token count {tokens} exceeds max {self.max_tokens}.")
            return MetricResult(self.name, 1.0, "passed", f"Token count {tokens} within limit.")

    custom = StrictCustomMetric()

    # Rejection of invalid config
    with pytest.raises(ValueError, match="max_tokens must be a positive integer"):
        custom.configure({"max_tokens": -5})
    assert custom.get_configuration_version() == 1
    assert custom.get_configuration() == {"max_tokens": 50}

    # Successful configuration
    custom.configure({"max_tokens": 5})
    assert custom.get_configuration_version() == 2
    assert custom.get_configuration() == {"max_tokens": 5}

    # Evaluation passes when within tokens
    res_pass = custom.evaluate(MetricContext(expected_behavior=None, actual_output="one two three", latency_ms=100))
    assert res_pass.score == 1.0
    assert res_pass.status == "passed"

    # Evaluation fails when exceeding tokens
    res_fail = custom.evaluate(MetricContext(expected_behavior=None, actual_output="one two three four five six", latency_ms=100))
    assert res_fail.score == 0.0
    assert res_fail.status == "failed"


# ---------------------------------------------------------------------------
# 4. Persistence Protection & Service Validation Tests
# ---------------------------------------------------------------------------

def test_service_execution_input_null_checks():
    """Verify execute_metrics rejects None inputs predictably."""
    with pytest.raises(ValueError, match="test_case cannot be None"):
        execute_metrics(None, TestRun(actual_output="ok", latency_ms=100))

    with pytest.raises(ValueError, match="test_run cannot be None"):
        execute_metrics(TestCase(expected_behavior="ok"), None)


def test_persistence_protection_on_invalid_status_and_missing_case(db):
    """Verify create_evaluation_result does not persist partial records on unready or missing entities."""
    # 1. Null checks
    with pytest.raises(ValueError, match="test_run cannot be None"):
        create_evaluation_result(None, db)

    with pytest.raises(ValueError, match="db session cannot be None"):
        create_evaluation_result(TestRun(id=uuid.uuid4()), None)

    # 2. TestRun in 'running' status (not completed or failed) -> 400 Bad Request
    running_run = TestRun(
        id=uuid.uuid4(),
        test_case_id=uuid.uuid4(),
        status="running",
        actual_output="in progress",
        latency_ms=100,
    )
    db.add(running_run)
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        create_evaluation_result(running_run, db)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Test run has not finished"

    # Verify no evaluation results persisted
    persisted_running = db.query(EvaluationResult).filter(EvaluationResult.test_run_id == running_run.id).all()
    assert len(persisted_running) == 0

    # 3. TestRun completed but test_case not found -> 404 Not Found
    orphan_run = TestRun(
        id=uuid.uuid4(),
        test_case_id=uuid.uuid4(),  # non-existent test case
        status="completed",
        actual_output="orphan result",
        latency_ms=100,
        result="passed",
    )
    db.add(orphan_run)
    db.commit()

    with pytest.raises(HTTPException) as exc_info_404:
        create_evaluation_result(orphan_run, db)
    assert exc_info_404.value.status_code == 404
    assert exc_info_404.value.detail == "Test case not found"

    persisted_orphan = db.query(EvaluationResult).filter(EvaluationResult.test_run_id == orphan_run.id).all()
    assert len(persisted_orphan) == 0

    # Clean up test records
    db.query(TestRun).filter(TestRun.id.in_([running_run.id, orphan_run.id])).delete(synchronize_session=False)
    db.commit()


def test_persistence_protection_transaction_rollback_on_invalid_data(db):
    """Verify that if any result model fails validation, database rolls back cleanly."""
    test_case = TestCase(
        id=uuid.uuid4(),
        evaluation_id=uuid.uuid4(),
        name="Rollback Safety TC",
        category="functional",
        input_data="input",
        expected_behavior="expected",
        is_adversarial=False,
    )
    db.add(test_case)
    db.commit()

    test_run = TestRun(
        id=uuid.uuid4(),
        test_case_id=test_case.id,
        status="completed",
        actual_output="expected",
        latency_ms=200,
        result="passed",
    )
    db.add(test_run)
    db.commit()

    # Attempting to add an invalid EvaluationResult (configuration_version = 0)
    with pytest.raises(ValueError):
        invalid_res = EvaluationResult(
            test_run_id=test_run.id,
            metric_name="invalid",
            status="passed",
            configuration_version=0,
        )
        db.add(invalid_res)
        db.commit()

    db.rollback()

    # Verify no results persisted
    persisted = db.query(EvaluationResult).filter(EvaluationResult.test_run_id == test_run.id).all()
    assert len(persisted) == 0

    # Cleanup
    db.query(TestRun).filter(TestRun.id == test_run.id).delete(synchronize_session=False)
    db.query(TestCase).filter(TestCase.id == test_case.id).delete(synchronize_session=False)
    db.commit()
