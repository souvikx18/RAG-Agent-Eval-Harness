import logging
import uuid
import pytest

from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.models.evaluation_result import EvaluationResult
from app.services.metric_execution_service import execute_metrics
from app.services.metrics.base_metric import Metric, MetricContext, MetricResult
from app.services.metrics.registry import MetricRegistry, metric_registry
from app.services.result_service import create_evaluation_result


def test_metric_evaluation_lifecycle_logging_success(caplog):
    """
    Step 186: Metric Evaluation Observability.
    Verifies that successful metric evaluations log:
    - Batch start event with test_run_id and metric count.
    - Per-metric evaluation start with metric name and test_run_id.
    - Successful completion with metric name, test_run_id, status, score, and duration_ms.
    """
    test_case = TestCase(
        id=uuid.uuid4(),
        input_data="Hello",
        expected_behavior="helpful greeting",
    )
    test_run = TestRun(
        id=uuid.uuid4(),
        test_case_id=test_case.id,
        actual_output="Hello! This is a helpful greeting.",
        latency_ms=250,
        status="completed",
        result="passed",
    )

    with caplog.at_level(logging.INFO, logger="veridyn.metrics"):
        results = execute_metrics(test_case, test_run)

    assert len(results) == 2
    log_messages = [record.getMessage() for record in caplog.records]
    combined_logs = " ".join(log_messages)

    run_id_str = str(test_run.id)

    # 1. Batch start
    assert any("Metric evaluation batch starting" in msg and run_id_str in msg for msg in log_messages)

    # 2. Per-metric start
    assert any("Metric evaluation starting: metric=correctness" in msg and run_id_str in msg for msg in log_messages)
    assert any("Metric evaluation starting: metric=latency" in msg and run_id_str in msg for msg in log_messages)

    # 3. Successful completions
    assert any("Metric evaluation completed successfully: metric=correctness" in msg and "status=passed" in msg and "score=1.00" in msg for msg in log_messages)
    assert any("Metric evaluation completed successfully: metric=latency" in msg and "status=passed" in msg and "score=1.00" in msg for msg in log_messages)

    # 4. Duration is recorded
    assert "duration_ms=" in combined_logs


def test_metric_evaluation_lifecycle_logging_validation_failure(caplog):
    """
    Verifies that expected validation failures log warning with diagnostic context (status, score, explanation).
    """
    test_case = TestCase(
        id=uuid.uuid4(),
        input_data="Prompt",
        expected_behavior="Strict expectation",
    )
    test_run = TestRun(
        id=uuid.uuid4(),
        test_case_id=test_case.id,
        actual_output="Different response",
        latency_ms=2500,  # exceeds high threshold
        status="completed",
        result="failed",
    )

    with caplog.at_level(logging.INFO, logger="veridyn.metrics"):
        results = execute_metrics(test_case, test_run)

    assert len(results) == 2
    log_records = caplog.records
    warnings = [r for r in log_records if r.levelno == logging.WARNING]

    run_id_str = str(test_run.id)

    # Correctness validation failure logged at WARNING
    correctness_warning = next((r for r in warnings if "metric=correctness" in r.getMessage()), None)
    assert correctness_warning is not None
    assert run_id_str in correctness_warning.getMessage()
    assert "status=failed" in correctness_warning.getMessage()
    assert "score=0.00" in correctness_warning.getMessage()
    assert "Expected behavior was not found" in correctness_warning.getMessage()

    # Latency validation failure logged at WARNING
    latency_warning = next((r for r in warnings if "metric=latency" in r.getMessage()), None)
    assert latency_warning is not None
    assert run_id_str in latency_warning.getMessage()
    assert "status=failed" in latency_warning.getMessage()
    assert "score=0.00" in latency_warning.getMessage()
    assert "Latency exceeds the target range" in latency_warning.getMessage()


def test_metric_evaluation_unexpected_exception_logging_and_isolation(caplog):
    """
    Verifies that an unexpected exception in one metric:
    - Is logged as ERROR with error details and duration.
    - Does NOT crash the execution loop.
    - Does NOT produce misleading success logs for that metric.
    - Allows subsequent metrics to execute and log normally.
    """
    class CrashingMetric(Metric):
        @property
        def name(self) -> str:
            return "crashing_metric"

        def evaluate(self, context: MetricContext) -> MetricResult:
            raise RuntimeError("Unexpected internal crash in metric computation")

    try:
        metric_registry.register(CrashingMetric())

        test_case = TestCase(
            id=uuid.uuid4(),
            input_data="input",
            expected_behavior="helpful",
        )
        test_run = TestRun(
            id=uuid.uuid4(),
            test_case_id=test_case.id,
            actual_output="helpful",
            latency_ms=100,
            status="completed",
            result="passed",
        )

        with caplog.at_level(logging.INFO, logger="veridyn.metrics"):
            results = execute_metrics(test_case, test_run)

        errors = [r for r in caplog.records if r.levelno == logging.ERROR]
        error_msgs = [r.getMessage() for r in errors]

        # Error is logged specifically for the crashing metric
        assert any("metric=crashing_metric" in msg and "Unexpected internal crash" in msg for msg in error_msgs)

        # No success log for crashing metric
        info_msgs = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO]
        assert not any("Metric evaluation completed successfully: metric=crashing_metric" in msg for msg in info_msgs)

        # Other metrics completed and logged successfully
        assert any("Metric evaluation completed successfully: metric=correctness" in msg for msg in info_msgs)
        assert any("Metric evaluation completed successfully: metric=latency" in msg for msg in info_msgs)

        # Returned result is failed with score 0.0
        crash_res = next(r for r in results if r.metric_result.metric_name == "crashing_metric")
        assert crash_res.metric_result.status == "failed"
        assert crash_res.metric_result.score == 0.0

    finally:
        metric_registry.reset()


def test_metric_registry_configuration_logging(caplog):
    """
    Verifies that MetricRegistry logs configuration success and validation failure cleanly.
    """
    registry = MetricRegistry()

    # Success logging
    with caplog.at_level(logging.INFO, logger="veridyn.metrics.registry"):
        registry.configure("correctness", {"case_sensitive": True})

    info_records = [r for r in caplog.records if r.levelno == logging.INFO and "veridyn.metrics.registry" in r.name]
    assert any("Metric configured successfully: metric=correctness version=2" in r.getMessage() for r in info_records)

    # Rejection logging
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="veridyn.metrics.registry"):
        with pytest.raises(ValueError):
            registry.configure("latency", {"fast_threshold_ms": -10})

    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING and "veridyn.metrics.registry" in r.name]
    assert any("Metric configuration rejected: metric=latency" in r.getMessage() and "cannot be negative" in r.getMessage() for r in warning_records)


def test_result_service_persistence_logging(db, caplog):
    """
    Verifies that create_evaluation_result logs processing start and successful database persistence.
    """
    test_case = TestCase(
        id=uuid.uuid4(),
        evaluation_id=uuid.uuid4(),
        name="Persistence Log TC",
        category="functional",
        input_data="input",
        expected_behavior="expected output",
        is_adversarial=False,
    )
    db.add(test_case)
    db.commit()

    test_run = TestRun(
        id=uuid.uuid4(),
        test_case_id=test_case.id,
        status="completed",
        actual_output="expected output",
        latency_ms=150,
        result="passed",
    )
    db.add(test_run)
    db.commit()

    with caplog.at_level(logging.INFO, logger="veridyn.evaluation_results"):
        results = create_evaluation_result(test_run, db)

    info_msgs = [r.getMessage() for r in caplog.records if "veridyn.evaluation_results" in r.name]
    run_id_str = str(test_run.id)

    assert any("Evaluation results processing starting" in msg and run_id_str in msg for msg in info_msgs)
    assert any("Evaluation results persisted successfully" in msg and run_id_str in msg and "result_count=2" in msg for msg in info_msgs)

    # Idempotent call logs existing
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="veridyn.evaluation_results"):
        second_call = create_evaluation_result(test_run, db)

    second_info_msgs = [r.getMessage() for r in caplog.records if "veridyn.evaluation_results" in r.name]
    assert any("Evaluation results already exist" in msg and run_id_str in msg for msg in second_info_msgs)

    # Clean up
    db.query(EvaluationResult).filter(EvaluationResult.test_run_id == test_run.id).delete(synchronize_session=False)
    db.query(TestRun).filter(TestRun.id == test_run.id).delete(synchronize_session=False)
    db.query(TestCase).filter(TestCase.id == test_case.id).delete(synchronize_session=False)
    db.commit()


def test_sensitive_information_is_never_logged(caplog):
    """
    Step 186: Protect sensitive information.
    Ensures that secrets, API keys, passwords, database credentials, and Bearer tokens
    present in input data, actual output, or environment are never leaked to logs.
    """
    sensitive_token = "sk-live-SUPER_SECRET_KEY_999888777"
    sensitive_password = "SuperSecretPassword123!"
    sensitive_db_url = "postgresql://admin:super_secret_pw@db.internal:5432/veridyn"
    sensitive_bearer = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.sensitive"

    test_case = TestCase(
        id=uuid.uuid4(),
        input_data=f"System prompt with {sensitive_password} and {sensitive_db_url}",
        expected_behavior=f"Authorization header: {sensitive_bearer}",
    )
    test_run = TestRun(
        id=uuid.uuid4(),
        test_case_id=test_case.id,
        actual_output=f"Leaked token: {sensitive_token} in response body",
        latency_ms=120,
        status="completed",
        result="passed",
    )

    with caplog.at_level(logging.DEBUG):
        results = execute_metrics(test_case, test_run)

    combined_logs = " ".join(record.getMessage() for record in caplog.records)

    # Verify none of the sensitive strings are in the captured log output
    assert sensitive_token not in combined_logs
    assert sensitive_password not in combined_logs
    assert sensitive_db_url not in combined_logs
    assert sensitive_bearer not in combined_logs
    assert "sk-live" not in combined_logs
    assert "super_secret" not in combined_logs.lower()
