import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.core.database import SessionLocal
from app.models.user import User
from app.models.agent import Agent
from app.models.agent_version import AgentVersion


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="module")
def authenticated_user_context(db_session):
    user = db_session.query(User).first()
    assert user is not None, "At least one user must exist in the database for integration tests"
    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    own_agent_version = (
        db_session.query(AgentVersion)
        .join(Agent, AgentVersion.agent_id == Agent.id)
        .filter(Agent.owner_id == user.id)
        .first()
    )
    assert own_agent_version is not None, "Authenticated user must own at least one AgentVersion"

    return {
        "user": user,
        "token": token,
        "headers": headers,
        "own_agent_version_id": str(own_agent_version.id),
    }


def test_get_evaluations_own_agent_version(client, authenticated_user_context):
    """
    Test A — Own AgentVersion:
    Authenticated user requests evaluations for an AgentVersion they own.
    Expectation: 200 OK and a list of evaluation records.
    """
    agent_version_id = authenticated_user_context["own_agent_version_id"]
    headers = authenticated_user_context["headers"]

    response = client.get(f"/evaluations/{agent_version_id}", headers=headers)

    assert response.status_code == 200
    evaluations = response.json()
    assert isinstance(evaluations, list)
    for item in evaluations:
        assert item["agent_version_id"] == agent_version_id
        assert "total_runs" in item
        assert "passed_runs" in item
        assert "failed_runs" in item
        assert "average_latency_ms" in item


def test_get_evaluations_unknown_agent_version(client, authenticated_user_context):
    """
    Test B — Unknown AgentVersion:
    Authenticated user requests evaluations for a non-existent or unowned AgentVersion.
    Expectation: 404 Not Found with detail 'Agent version not found'.
    """
    unknown_agent_version_id = "00000000-0000-0000-0000-000000000001"
    headers = authenticated_user_context["headers"]

    response = client.get(f"/evaluations/{unknown_agent_version_id}", headers=headers)

    assert response.status_code == 404
    body = response.json()
    assert body.get("detail") == "Agent version not found"


def test_get_evaluations_missing_jwt(client, authenticated_user_context):
    """
    Edge Case — Missing JWT:
    Anonymous request without Authorization header must be rejected.
    Expectation: 401 Unauthorized / Not authenticated.
    """
    agent_version_id = authenticated_user_context["own_agent_version_id"]

    response = client.get(f"/evaluations/{agent_version_id}")

    assert response.status_code == 401


def test_create_evaluation_unknown_agent_version(client, authenticated_user_context):
    """
    POST /evaluations with unknown/unowned agent_version_id:
    Expectation: 404 Not Found.
    """
    headers = authenticated_user_context["headers"]
    payload = {
        "agent_version_id": "00000000-0000-0000-0000-000000000001",
        "trigger_type": "manual",
    }

    response = client.post("/evaluations", json=payload, headers=headers)

    assert response.status_code == 404
    assert response.json().get("detail") == "Agent version not found"


def test_get_evaluations_statistics_values(client, authenticated_user_context, db_session):
    """
    Test — Evaluation statistics values:
    Verify that the Evaluation API returns correct statistics
    for an evaluation with multiple test runs.
    """
    from app.models.evaluation import Evaluation
    from app.models.test_case import TestCase
    from app.models.test_run import TestRun

    agent_version_id = uuid.UUID(
        authenticated_user_context["own_agent_version_id"]
    )
    headers = authenticated_user_context["headers"]

    evaluation = Evaluation(
        agent_version_id=agent_version_id,
        status="completed",
        trigger_type="manual",
    )
    db_session.add(evaluation)
    db_session.commit()
    db_session.refresh(evaluation)

    test_case = TestCase(
        evaluation_id=evaluation.id,
        name="API Statistics Test",
        category="functional",
        input_data="Hello",
        expected_behavior="Successful response",
        is_adversarial=False,
    )
    db_session.add(test_case)
    db_session.commit()
    db_session.refresh(test_case)

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
        latency_ms=200,
    )

    run_three = TestRun(
        test_case_id=test_case.id,
        status="failed",
        result="failed",
        latency_ms=300,
    )

    db_session.add_all([run_one, run_two, run_three])
    db_session.commit()

    response = client.get(
        f"/evaluations/{agent_version_id}",
        headers=headers,
    )

    assert response.status_code == 200

    evaluations = response.json()

    matching_evaluation = next(
        item
        for item in evaluations
        if item["id"] == str(evaluation.id)
    )

    assert matching_evaluation["total_runs"] == 3
    assert matching_evaluation["passed_runs"] == 2
    assert matching_evaluation["failed_runs"] == 1
    assert matching_evaluation["average_latency_ms"] == 200.0


def test_evaluation_api_metric_configurations(client, authenticated_user_context, db_session):
    from app.models.evaluation import Evaluation
    from app.models.evaluation_result import EvaluationResult
    from app.models.test_case import TestCase
    from app.models.test_run import TestRun

    agent_version_id = uuid.UUID(
        authenticated_user_context["own_agent_version_id"]
    )
    headers = authenticated_user_context["headers"]

    # 1. Evaluation with no results returns {}
    create_response = client.post(
        "/evaluations",
        json={
            "agent_version_id": str(agent_version_id),
            "trigger_type": "manual",
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    assert create_response.json()["metric_configurations"] == {}

    # 2. Evaluation with results returns persisted metric configurations
    evaluation_id = uuid.UUID(create_response.json()["id"])
    test_case = TestCase(
        evaluation_id=evaluation_id,
        name="Metric Config Test Case",
        category="functional",
        input_data="Hello",
        expected_behavior="Expected",
        is_adversarial=False,
    )
    db_session.add(test_case)
    db_session.commit()
    db_session.refresh(test_case)

    test_run = TestRun(
        test_case_id=test_case.id,
        status="completed",
        result="passed",
        actual_output="Expected",
        latency_ms=150,
    )
    db_session.add(test_run)
    db_session.commit()
    db_session.refresh(test_run)

    result_correctness = EvaluationResult(
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
    result_latency = EvaluationResult(
        test_run_id=test_run.id,
        metric_name="latency",
        score=0.9,
        status="passed",
        explanation="Fast",
        configuration_version=3,
        configuration={
            "fast_threshold_ms": 300,
            "acceptable_threshold_ms": 800,
            "high_threshold_ms": 1500,
        },
    )
    db_session.add_all([result_correctness, result_latency])
    db_session.commit()

    # Move evaluation status to running so complete endpoint succeeds
    eval_record = db_session.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
    eval_record.status = "running"
    db_session.commit()

    complete_response = client.post(
        f"/evaluations/{evaluation_id}/complete",
        headers=headers,
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["metric_configurations"]["correctness"]["version"] == 2
    assert complete_response.json()["metric_configurations"]["correctness"]["configuration"] == {
        "case_sensitive": True,
    }
    assert complete_response.json()["metric_configurations"]["latency"]["version"] == 3
    assert complete_response.json()["metric_configurations"]["latency"]["configuration"] == {
        "fast_threshold_ms": 300,
        "acceptable_threshold_ms": 800,
        "high_threshold_ms": 1500,
    }

    # Also verify GET returns the metric configurations
    get_response = client.get(
        f"/evaluations/{agent_version_id}",
        headers=headers,
    )
    assert get_response.status_code == 200
    matching = next(
        item for item in get_response.json() if item["id"] == str(evaluation_id)
    )
    assert matching["metric_configurations"]["correctness"]["version"] == 2
    assert matching["metric_configurations"]["correctness"]["configuration"] == {
        "case_sensitive": True,
    }


def test_evaluation_api_metric_configuration_consistency_with_persisted_results(
    client, authenticated_user_context, db_session
):
    from app.models.evaluation import Evaluation
    from app.models.evaluation_result import EvaluationResult
    from app.models.test_case import TestCase
    from app.models.test_run import TestRun
    from app.services.metrics.registry import metric_registry

    # Reset registry to default state (version 1) to verify API does not rely on global registry state
    metric_registry.reset()

    agent_version_id = uuid.UUID(
        authenticated_user_context["own_agent_version_id"]
    )
    headers = authenticated_user_context["headers"]

    evaluation = Evaluation(
        agent_version_id=agent_version_id,
        status="running",
        trigger_type="manual",
    )
    db_session.add(evaluation)
    db_session.commit()
    db_session.refresh(evaluation)

    test_case = TestCase(
        evaluation_id=evaluation.id,
        name="Consistency Test Case",
        category="functional",
        input_data="Query",
        expected_behavior="Target",
        is_adversarial=False,
    )
    db_session.add(test_case)
    db_session.commit()
    db_session.refresh(test_case)

    test_run = TestRun(
        test_case_id=test_case.id,
        status="completed",
        result="passed",
        actual_output="Target",
        latency_ms=100,
    )
    db_session.add(test_run)
    db_session.commit()
    db_session.refresh(test_run)

    result_correctness = EvaluationResult(
        test_run_id=test_run.id,
        metric_name="correctness",
        score=1.0,
        status="passed",
        explanation="Exact match",
        configuration_version=2,
        configuration={
            "case_sensitive": True,
        },
    )
    result_latency = EvaluationResult(
        test_run_id=test_run.id,
        metric_name="latency",
        score=1.0,
        status="passed",
        explanation="Fast latency",
        configuration_version=3,
        configuration={
            "fast_threshold_ms": 300,
            "acceptable_threshold_ms": 800,
            "high_threshold_ms": 1500,
        },
    )
    db_session.add_all([result_correctness, result_latency])
    db_session.commit()

    response = client.post(
        f"/evaluations/{evaluation.id}/complete",
        headers=headers,
    )
    assert response.status_code == 200

    assert response.json()["metric_configurations"]["correctness"] == {
        "version": 2,
        "configuration": {
            "case_sensitive": True,
        },
    }
    assert response.json()["metric_configurations"]["latency"] == {
        "version": 3,
        "configuration": {
            "fast_threshold_ms": 300,
            "acceptable_threshold_ms": 800,
            "high_threshold_ms": 1500,
        },
    }

    get_response = client.get(
        f"/evaluations/{agent_version_id}",
        headers=headers,
    )
    assert get_response.status_code == 200
    matching = next(
        item for item in get_response.json() if item["id"] == str(evaluation.id)
    )
    assert matching["metric_configurations"]["correctness"] == {
        "version": 2,
        "configuration": {
            "case_sensitive": True,
        },
    }
    assert matching["metric_configurations"]["latency"] == {
        "version": 3,
        "configuration": {
            "fast_threshold_ms": 300,
            "acceptable_threshold_ms": 800,
            "high_threshold_ms": 1500,
        },
    }



