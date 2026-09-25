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

    evaluation = (
        db_session.query(Evaluation)
        .join(AgentVersion, Evaluation.agent_version_id == AgentVersion.id)
        .join(Agent, AgentVersion.agent_id == Agent.id)
        .filter(Agent.owner_id == user.id)
        .first()
    )
    assert evaluation is not None, "User must own at least one Evaluation"

    return {
        "user": user,
        "token": token,
        "headers": headers,
        "own_evaluation_id": str(evaluation.id),
    }


def test_get_deployment_gates_own_evaluation(client, authenticated_context):
    """
    Test A — Own Evaluation:
    Call GET /evaluations/{YOUR_EVALUATION_ID}/deployment-gate
    Expected: 200 OK
    """
    evaluation_id = authenticated_context["own_evaluation_id"]
    headers = authenticated_context["headers"]

    response = client.get(
        f"/evaluations/{evaluation_id}/deployment-gate",
        headers=headers,
    )

    assert response.status_code == 200
    gates = response.json()
    assert isinstance(gates, list)


def test_get_deployment_gates_unknown_evaluation(client, authenticated_context):
    """
    Test B — Unknown Evaluation:
    Call GET /evaluations/00000000-0000-0000-0000-000000000001/deployment-gate
    Expected: 404 Not Found with detail 'Evaluation not found'
    """
    unknown_id = "00000000-0000-0000-0000-000000000001"
    headers = authenticated_context["headers"]

    response = client.get(
        f"/evaluations/{unknown_id}/deployment-gate",
        headers=headers,
    )

    assert response.status_code == 404
    body = response.json()
    assert body.get("detail") == "Evaluation not found"


def test_create_deployment_gate_unauthorized(client, authenticated_context):
    """
    Test C — Unauthorized Gate Creation:
    Call POST /evaluations/00000000-0000-0000-0000-000000000001/deployment-gate
    Expected: 404 Not Found
    """
    unknown_id = "00000000-0000-0000-0000-000000000001"
    headers = authenticated_context["headers"]

    response = client.post(
        f"/evaluations/{unknown_id}/deployment-gate",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json().get("detail") == "Evaluation not found"


def test_get_deployment_gates_missing_jwt(client, authenticated_context):
    """
    Acceptance Criteria — JWT Required:
    Missing Authorization header must return 401 Unauthorized.
    """
    evaluation_id = authenticated_context["own_evaluation_id"]

    response = client.get(f"/evaluations/{evaluation_id}/deployment-gate")

    assert response.status_code == 401
