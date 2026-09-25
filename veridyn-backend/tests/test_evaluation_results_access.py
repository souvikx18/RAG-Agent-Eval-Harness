import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.core.database import SessionLocal
from app.models.user import User
from app.models.agent import Agent
from app.models.agent_version import AgentVersion
from app.models.evaluation import Evaluation
from app.models.test_case import TestCase
from app.models.test_run import TestRun


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="module")
def authenticated_context(db_session):
    user = db_session.query(User).first()
    assert user is not None, "A user must exist for integration tests"
    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    test_run = (
        db_session.query(TestRun)
        .join(TestCase, TestRun.test_case_id == TestCase.id)
        .join(Evaluation, TestCase.evaluation_id == Evaluation.id)
        .join(AgentVersion, Evaluation.agent_version_id == AgentVersion.id)
        .join(Agent, AgentVersion.agent_id == Agent.id)
        .filter(Agent.owner_id == user.id)
        .first()
    )
    assert test_run is not None, "User must own at least one TestRun"

    return {
        "user": user,
        "token": token,
        "headers": headers,
        "own_test_run_id": str(test_run.id),
    }


def test_get_evaluation_results_own_test_run(client, authenticated_context):
    """
    Test A — Own TestRun:
    Call GET /test-runs/{YOUR_TEST_RUN_ID}/results
    Expected: 200 OK
    """
    test_run_id = authenticated_context["own_test_run_id"]
    headers = authenticated_context["headers"]

    response = client.get(f"/test-runs/{test_run_id}/results", headers=headers)

    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)


def test_get_evaluation_results_unknown_test_run(client, authenticated_context):
    """
    Test B — Unknown TestRun:
    Call GET /test-runs/00000000-0000-0000-0000-000000000001/results
    Expected: 404 Not Found with detail 'Test run not found'
    """
    unknown_id = "00000000-0000-0000-0000-000000000001"
    headers = authenticated_context["headers"]

    response = client.get(f"/test-runs/{unknown_id}/results", headers=headers)

    assert response.status_code == 404
    body = response.json()
    assert body.get("detail") == "Test run not found"


def test_create_evaluation_result_unauthorized(client, authenticated_context):
    """
    Test C — Unauthorized result creation:
    Call POST /test-runs/00000000-0000-0000-0000-000000000001/results
    Expected: 404 Not Found
    """
    unknown_id = "00000000-0000-0000-0000-000000000001"
    headers = authenticated_context["headers"]
    payload = {
        "metric_name": "authorization_test",
        "score": 1.0,
        "status": "passed",
        "explanation": "Authorization test",
    }

    response = client.post(
        f"/test-runs/{unknown_id}/results",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json().get("detail") == "Test run not found"


def test_get_evaluation_results_missing_jwt(client, authenticated_context):
    """
    Acceptance Criteria — JWT Required:
    Missing Authorization header must return 401 Unauthorized.
    """
    test_run_id = authenticated_context["own_test_run_id"]

    response = client.get(f"/test-runs/{test_run_id}/results")

    assert response.status_code == 401
