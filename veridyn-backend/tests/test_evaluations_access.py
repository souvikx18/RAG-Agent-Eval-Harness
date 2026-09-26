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
