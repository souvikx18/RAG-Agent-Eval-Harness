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

    test_case = (
        db_session.query(TestCase)
        .join(Evaluation, TestCase.evaluation_id == Evaluation.id)
        .join(AgentVersion, Evaluation.agent_version_id == AgentVersion.id)
        .join(Agent, AgentVersion.agent_id == Agent.id)
        .filter(Agent.owner_id == user.id)
        .first()
    )
    assert test_case is not None, "User must own at least one TestCase"

    return {
        "user": user,
        "token": token,
        "headers": headers,
        "own_test_case_id": str(test_case.id),
    }


def test_get_test_runs_own_test_case(client, authenticated_context):
    """
    Test A — Own TestCase:
    Call GET /test-cases/{YOUR_TEST_CASE_ID}/runs
    Expected: 200 OK
    """
    test_case_id = authenticated_context["own_test_case_id"]
    headers = authenticated_context["headers"]

    response = client.get(f"/test-cases/{test_case_id}/runs", headers=headers)

    assert response.status_code == 200
    runs = response.json()
    assert isinstance(runs, list)


def test_get_test_runs_unknown_test_case(client, authenticated_context):
    """
    Test B — Unknown TestCase:
    Call GET /test-cases/00000000-0000-0000-0000-000000000001/runs
    Expected: 404 Not Found with detail 'Test case not found'
    """
    unknown_id = "00000000-0000-0000-0000-000000000001"
    headers = authenticated_context["headers"]

    response = client.get(f"/test-cases/{unknown_id}/runs", headers=headers)

    assert response.status_code == 404
    body = response.json()
    assert body.get("detail") == "Test case not found"


def test_create_test_run_unknown_test_case(client, authenticated_context):
    """
    Test C — Unauthorized creation:
    Call POST /test-cases/00000000-0000-0000-0000-000000000001/runs
    Expected: 404 Not Found
    """
    unknown_id = "00000000-0000-0000-0000-000000000001"
    headers = authenticated_context["headers"]

    response = client.post(f"/test-cases/{unknown_id}/runs", headers=headers)

    assert response.status_code == 404
    assert response.json().get("detail") == "Test case not found"


def test_get_test_runs_missing_jwt(client, authenticated_context):
    """
    Acceptance Criteria — JWT Required:
    Missing Authorization header must return 401 Unauthorized.
    """
    test_case_id = authenticated_context["own_test_case_id"]

    response = client.get(f"/test-cases/{test_case_id}/runs")

    assert response.status_code == 401
