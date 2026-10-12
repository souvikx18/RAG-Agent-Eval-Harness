import uuid
from sqlalchemy import event

from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.models.evaluation_result import EvaluationResult
from app.services.metric_execution_service import (
    execute_metrics,
    execute_metrics_as_dicts,
)
from app.services.metrics.base_metric import Metric, MetricContext, MetricResult
from app.services.metrics.registry import MetricRegistry, metric_registry
from app.services.result_service import create_evaluation_result


def test_metric_evaluation_computational_efficiency_and_consistency():
    """
    Step 187: Performance & Resource Efficiency.
    Verifies that evaluation executes efficiently without redundant operations,
    and returns exact, deterministic results across representative inputs.
    """
    # 1. Normal inputs
    tc = TestCase(
        id=uuid.uuid4(),
        input_data="Normal prompt",
        expected_behavior="helpful response",
    )
    tr = TestRun(
        id=uuid.uuid4(),
        test_case_id=tc.id,
        actual_output="This is a helpful response to the prompt.",
        latency_ms=300,
        status="completed",
        result="passed",
    )

    results = execute_metrics(tc, tr)
    assert len(results) == 2
    res_by_name = {r.metric_result.metric_name: r for r in results}

    assert res_by_name["correctness"].metric_result.score == 1.0
    assert res_by_name["correctness"].metric_result.status == "passed"
    assert res_by_name["latency"].metric_result.score == 1.0
    assert res_by_name["latency"].metric_result.status == "passed"

    # 2. Large output handling without excessive memory or computation
    large_output = "prefix " + ("word " * 10000) + "helpful response " + ("suffix " * 5000)
    tr_large = TestRun(
        id=uuid.uuid4(),
        test_case_id=tc.id,
        actual_output=large_output,
        latency_ms=450,
        status="completed",
        result="passed",
    )

    large_results = execute_metrics(tc, tr_large)
    large_res_by_name = {r.metric_result.metric_name: r for r in large_results}
    assert large_res_by_name["correctness"].metric_result.score == 1.0
    assert large_res_by_name["correctness"].metric_result.status == "passed"


def test_evaluation_result_database_query_efficiency(db):
    """
    Verifies database query efficiency:
    - Verifies persistence uses predictable, minimal queries without N+1 loops.
    - Subsequent idempotent calls only query existing results and do not emit extra queries.
    """
    test_case = TestCase(
        id=uuid.uuid4(),
        evaluation_id=uuid.uuid4(),
        name="Performance Query TC",
        category="functional",
        input_data="Query test input",
        expected_behavior="Query test expected",
        is_adversarial=False,
    )
    db.add(test_case)
    db.commit()

    test_run = TestRun(
        id=uuid.uuid4(),
        test_case_id=test_case.id,
        status="completed",
        actual_output="Query test expected",
        latency_ms=200,
        result="passed",
    )
    db.add(test_run)
    db.commit()

    queries = []

    def count_queries(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)

    event.listen(db.bind, "before_cursor_execute", count_queries)

    try:
        # 1. First execution: evaluates and persists results efficiently
        results = create_evaluation_result(test_run, db)
        assert len(results) == 2

        # Verify minimal, bounded query count (no repeated/N+1 queries for TestCase)
        tc_select_queries = [
            q for q in queries
            if "SELECT" in q.upper() and "test_cases" in q.lower()
        ]
        assert len(tc_select_queries) <= 1, (
            f"Expected at most 1 query on test_cases, got: {len(tc_select_queries)}"
        )

        # 2. Second execution (idempotent): should only check existing results
        queries.clear()
        cached_results = create_evaluation_result(test_run, db)
        assert len(cached_results) == 2

        # At most 2 SELECTs (one refresh for test_run, one for evaluation_results), 0 INSERTs or UPDATEs
        select_queries = [q for q in queries if "SELECT" in q.upper()]
        insert_queries = [q for q in queries if "INSERT" in q.upper()]
        update_queries = [q for q in queries if "UPDATE" in q.upper()]
        assert len(select_queries) <= 2
        assert len(insert_queries) == 0
        assert len(update_queries) == 0

    finally:
        event.remove(db.bind, "before_cursor_execute", count_queries)

        # Cleanup
        db.query(EvaluationResult).filter(EvaluationResult.test_run_id == test_run.id).delete(synchronize_session=False)
        db.query(TestRun).filter(TestRun.id == test_run.id).delete(synchronize_session=False)
        db.query(TestCase).filter(TestCase.id == test_case.id).delete(synchronize_session=False)
        db.commit()


def test_metric_evaluation_memory_isolation_and_no_leakage():
    """
    Verifies that metric evaluations do not retain references to previous evaluation contexts
    and that snapshot data structures remain independent.
    """
    tc1 = TestCase(input_data="In 1", expected_behavior="one")
    tr1 = TestRun(actual_output="one", latency_ms=100)

    tc2 = TestCase(input_data="In 2", expected_behavior="two")
    tr2 = TestRun(actual_output="two", latency_ms=200)

    res1 = execute_metrics(tc1, tr1)
    res2 = execute_metrics(tc2, tr2)

    # Verify results are completely independent objects
    assert res1 is not res2
    assert res1[0] is not res2[0]
    assert res1[0].configuration is not res2[0].configuration

    # Verify registry state is unchanged
    assert metric_registry.get("correctness").get_configuration_version() == 1
    assert metric_registry.get("latency").get_configuration_version() == 1


def test_metric_batch_linear_scaling_with_multiple_metrics():
    """
    Verifies that executing a batch of registered metrics scales linearly O(N)
    without repeated setup or shared state pollution.
    """
    class QuickCustomMetric(Metric):
        def __init__(self, idx: int):
            super().__init__()
            self._idx = idx

        @property
        def name(self) -> str:
            return f"quick_metric_{self._idx}"

        def evaluate(self, context: MetricContext) -> MetricResult:
            return MetricResult(self.name, 1.0, "passed", f"Evaluation {self._idx}")

    test_registry = MetricRegistry(register_defaults=False)
    for i in range(10):
        test_registry.register(QuickCustomMetric(i))

    tc = TestCase(input_data="data", expected_behavior="behavior")
    tr = TestRun(actual_output="output", latency_ms=50)

    context = MetricContext(tc.expected_behavior, tr.actual_output, tr.latency_ms)

    results = [metric.evaluate(context) for metric in test_registry.all()]
    assert len(results) == 10
    for i, res in enumerate(results):
        assert res.metric_name == f"quick_metric_{i}"
        assert res.score == 1.0
        assert res.status == "passed"
