import uuid

from app.models.evaluation import Evaluation
from app.models.evaluation_result import EvaluationResult
from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.services.evaluation_statistics_service import (
    calculate_evaluation_statistics,
    get_evaluation_metric_configurations,
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


def test_evaluation_statistics_isolated_between_evaluations(db):
    evaluation_one = Evaluation(
        agent_version_id=uuid.uuid4(),
        status="completed",
        trigger_type="manual",
    )

    evaluation_two = Evaluation(
        agent_version_id=uuid.uuid4(),
        status="completed",
        trigger_type="manual",
    )

    db.add_all([evaluation_one, evaluation_two])
    db.commit()
    db.refresh(evaluation_one)
    db.refresh(evaluation_two)

    test_case_one = TestCase(
        evaluation_id=evaluation_one.id,
        name="Evaluation One Test",
        category="functional",
        input_data="Hello",
        expected_behavior="Successful response",
        is_adversarial=False,
    )

    test_case_two = TestCase(
        evaluation_id=evaluation_two.id,
        name="Evaluation Two Test",
        category="functional",
        input_data="Hello",
        expected_behavior="Successful response",
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
        status="failed",
        result="failed",
        latency_ms=500,
    )

    db.add_all([run_one, run_two])
    db.commit()

    statistics_one = calculate_evaluation_statistics(
        evaluation_one,
        db,
    )

    statistics_two = calculate_evaluation_statistics(
        evaluation_two,
        db,
    )

    assert statistics_one["total_runs"] == 1
    assert statistics_one["passed_runs"] == 1
    assert statistics_one["failed_runs"] == 0
    assert statistics_one["average_latency_ms"] == 100.0

    assert statistics_two["total_runs"] == 1
    assert statistics_two["passed_runs"] == 0
    assert statistics_two["failed_runs"] == 1
    assert statistics_two["average_latency_ms"] == 500.0


def test_evaluation_statistics_independent_of_run_order(db):
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
        name="Run Order Test",
        category="functional",
        input_data="Hello",
        expected_behavior="Successful response",
        is_adversarial=False,
    )
    db.add(test_case)
    db.commit()
    db.refresh(test_case)

    run_failed = TestRun(
        test_case_id=test_case.id,
        status="failed",
        result="failed",
        latency_ms=400,
    )

    run_passed = TestRun(
        test_case_id=test_case.id,
        status="completed",
        result="passed",
        latency_ms=100,
    )

    run_failed_second = TestRun(
        test_case_id=test_case.id,
        status="failed",
        result="failed",
        latency_ms=200,
    )

    db.add_all([
        run_failed,
        run_passed,
        run_failed_second,
    ])
    db.commit()

    statistics = calculate_evaluation_statistics(
        evaluation,
        db,
    )

    assert statistics["total_runs"] == 3
    assert statistics["passed_runs"] == 1
    assert statistics["failed_runs"] == 2
    assert statistics["average_latency_ms"] == 233.33


def test_evaluation_statistics_with_running_run(db):
    evaluation = Evaluation(
        agent_version_id=uuid.uuid4(),
        status="running",
        trigger_type="manual",
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)

    test_case = TestCase(
        evaluation_id=evaluation.id,
        name="Running Run Test",
        category="reliability",
        input_data="Hello",
        expected_behavior="Successful response",
        is_adversarial=False,
    )
    db.add(test_case)
    db.commit()
    db.refresh(test_case)

    completed_run = TestRun(
        test_case_id=test_case.id,
        status="completed",
        result="passed",
        latency_ms=100,
    )

    running_run = TestRun(
        test_case_id=test_case.id,
        status="running",
        result=None,
        latency_ms=None,
    )

    db.add_all([completed_run, running_run])
    db.commit()

    statistics = calculate_evaluation_statistics(
        evaluation,
        db,
    )

    assert statistics["total_runs"] == 2
    assert statistics["passed_runs"] == 1
    assert statistics["failed_runs"] == 0
    assert statistics["average_latency_ms"] == 100.0


def test_evaluation_statistics_with_mixed_run_states(db):
    evaluation = Evaluation(
        agent_version_id=uuid.uuid4(),
        status="running",
        trigger_type="manual",
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)

    test_case = TestCase(
        evaluation_id=evaluation.id,
        name="Mixed Run States Test",
        category="reliability",
        input_data="Hello",
        expected_behavior="Successful response",
        is_adversarial=False,
    )
    db.add(test_case)
    db.commit()
    db.refresh(test_case)

    run_passed_one = TestRun(
        test_case_id=test_case.id,
        status="completed",
        result="passed",
        latency_ms=100,
    )

    run_passed_two = TestRun(
        test_case_id=test_case.id,
        status="completed",
        result="passed",
        latency_ms=200,
    )

    run_failed_result = TestRun(
        test_case_id=test_case.id,
        status="completed",
        result="failed",
        latency_ms=300,
    )

    run_failed_status = TestRun(
        test_case_id=test_case.id,
        status="failed",
        result="failed",
        latency_ms=400,
    )

    run_running = TestRun(
        test_case_id=test_case.id,
        status="running",
        result=None,
        latency_ms=None,
    )

    run_missing_latency = TestRun(
        test_case_id=test_case.id,
        status="completed",
        result="passed",
        latency_ms=None,
    )

    db.add_all([
        run_passed_one,
        run_passed_two,
        run_failed_result,
        run_failed_status,
        run_running,
        run_missing_latency,
    ])
    db.commit()

    statistics = calculate_evaluation_statistics(
        evaluation,
        db,
    )

    assert statistics["total_runs"] == 6
    assert statistics["passed_runs"] == 3
    assert statistics["failed_runs"] == 2
    assert statistics["average_latency_ms"] == 250.0


def test_get_evaluation_metric_configurations_no_results(db):
    evaluation = Evaluation(
        agent_version_id=uuid.uuid4(),
        status="completed",
        trigger_type="manual",
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)

    configs = get_evaluation_metric_configurations(evaluation, db)
    assert configs == {}


def test_get_evaluation_metric_configurations_multiple_metrics(db):
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
        name="Multi Metric Test Case",
        category="functional",
        input_data="input data",
        expected_behavior="expected output",
    )
    db.add(test_case)
    db.commit()
    db.refresh(test_case)

    test_run = TestRun(
        test_case_id=test_case.id,
        status="completed",
        result="passed",
        actual_output="actual output",
        latency_ms=120,
    )
    db.add(test_run)
    db.commit()
    db.refresh(test_run)

    res_correctness = EvaluationResult(
        test_run_id=test_run.id,
        metric_name="correctness",
        score=1.0,
        status="passed",
        explanation="Accurate response",
        configuration_version=2,
        configuration={
            "case_sensitive": True,
        },
    )

    res_latency = EvaluationResult(
        test_run_id=test_run.id,
        metric_name="latency",
        score=0.9,
        status="passed",
        explanation="Low latency execution",
        configuration_version=3,
        configuration={
            "fast_threshold_ms": 300,
            "acceptable_threshold_ms": 800,
            "high_threshold_ms": 1500,
        },
    )

    db.add_all([res_correctness, res_latency])
    db.commit()

    configs = get_evaluation_metric_configurations(evaluation, db)

    expected = {
        "correctness": {
            "version": 2,
            "configuration": {
                "case_sensitive": True,
            },
        },
        "latency": {
            "version": 3,
            "configuration": {
                "fast_threshold_ms": 300,
                "acceptable_threshold_ms": 800,
                "high_threshold_ms": 1500,
            },
        },
    }

    assert configs == expected


def test_get_evaluation_metric_configurations_isolation(db):
    eval_a = Evaluation(
        agent_version_id=uuid.uuid4(),
        status="completed",
        trigger_type="manual",
    )
    eval_b = Evaluation(
        agent_version_id=uuid.uuid4(),
        status="completed",
        trigger_type="manual",
    )
    db.add_all([eval_a, eval_b])
    db.commit()
    db.refresh(eval_a)
    db.refresh(eval_b)

    tc_a = TestCase(
        evaluation_id=eval_a.id,
        name="Case A",
        category="functional",
        input_data="In A",
        expected_behavior="Out A",
    )
    tc_b = TestCase(
        evaluation_id=eval_b.id,
        name="Case B",
        category="functional",
        input_data="In B",
        expected_behavior="Out B",
    )
    db.add_all([tc_a, tc_b])
    db.commit()
    db.refresh(tc_a)
    db.refresh(tc_b)

    tr_a = TestRun(test_case_id=tc_a.id, status="completed", latency_ms=50)
    tr_b = TestRun(test_case_id=tc_b.id, status="completed", latency_ms=80)
    db.add_all([tr_a, tr_b])
    db.commit()
    db.refresh(tr_a)
    db.refresh(tr_b)

    res_a = EvaluationResult(
        test_run_id=tr_a.id,
        metric_name="correctness",
        score=1.0,
        status="passed",
        explanation="Eval A result",
        configuration_version=1,
        configuration={"model": "gpt-4"},
    )
    res_b = EvaluationResult(
        test_run_id=tr_b.id,
        metric_name="correctness",
        score=0.8,
        status="passed",
        explanation="Eval B result",
        configuration_version=4,
        configuration={"model": "claude-3"},
    )
    db.add_all([res_a, res_b])
    db.commit()

    configs_a = get_evaluation_metric_configurations(eval_a, db)
    configs_b = get_evaluation_metric_configurations(eval_b, db)

    assert configs_a == {
        "correctness": {
            "version": 1,
            "configuration": {"model": "gpt-4"},
        }
    }
    assert configs_b == {
        "correctness": {
            "version": 4,
            "configuration": {"model": "claude-3"},
        }
    }


def test_get_evaluation_metric_configurations_mutation_protection(db):
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
        name="Mutation Test Case",
        category="functional",
        input_data="input",
        expected_behavior="output",
    )
    db.add(test_case)
    db.commit()
    db.refresh(test_case)

    test_run = TestRun(
        test_case_id=test_case.id,
        status="completed",
        result="passed",
        latency_ms=100,
    )
    db.add(test_run)
    db.commit()
    db.refresh(test_run)

    result = EvaluationResult(
        test_run_id=test_run.id,
        metric_name="correctness",
        score=1.0,
        status="passed",
        explanation="Accurate",
        configuration_version=2,
        configuration={
            "case_sensitive": True,
        },
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    snapshot = get_evaluation_metric_configurations(
        evaluation,
        db,
    )

    snapshot["correctness"]["configuration"]["case_sensitive"] = False

    assert result.configuration == {
        "case_sensitive": True,
    }


def test_metric_configuration_snapshot_immutability(db):
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
        name="Snapshot Immutability Test Case",
        category="functional",
        input_data="input data",
        expected_behavior="expected output",
    )
    db.add(test_case)
    db.commit()
    db.refresh(test_case)

    test_run = TestRun(
        test_case_id=test_case.id,
        status="completed",
        result="passed",
        latency_ms=100,
    )
    db.add(test_run)
    db.commit()
    db.refresh(test_run)

    result = EvaluationResult(
        test_run_id=test_run.id,
        metric_name="correctness",
        score=1.0,
        status="passed",
        explanation="Accurate response",
        configuration_version=2,
        configuration={
            "case_sensitive": True,
        },
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    # 1. Obtain snapshot from evaluation service
    snapshot = get_evaluation_metric_configurations(
        evaluation,
        db,
    )

    # 2. Mutate the returned snapshot
    snapshot["correctness"]["configuration"]["case_sensitive"] = False

    # 3. Fetch the EvaluationResult again from the database
    db.refresh(result)
    persisted_result = (
        db.query(EvaluationResult)
        .filter(EvaluationResult.id == result.id)
        .first()
    )

    # 4. Verify persisted configuration and version remain unchanged
    assert persisted_result.configuration == {
        "case_sensitive": True,
    }
    assert persisted_result.configuration_version == 2

    # 5. Verify the snapshot itself actually changed
    assert snapshot["correctness"]["configuration"] == {
        "case_sensitive": False,
    }
    assert snapshot["correctness"]["version"] == 2








