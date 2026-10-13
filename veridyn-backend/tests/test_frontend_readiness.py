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
def context(db_session):
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

    evaluation = (
        db_session.query(Evaluation)
        .filter(Evaluation.id == test_case.evaluation_id)
        .first()
    )
    agent_version = (
        db_session.query(AgentVersion)
        .filter(AgentVersion.id == evaluation.agent_version_id)
        .first()
    )

    return {
        "user": user,
        "token": token,
        "headers": headers,
        "test_case": test_case,
        "evaluation": evaluation,
        "agent_version": agent_version,
    }


def test_cors_middleware_headers(client):
    """CORS middleware must return appropriate access-control headers for frontend clients."""
    origin = "http://localhost:5173"
    response = client.get(
        "/health",
        headers={"Origin": origin},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_preflight_options(client):
    """OPTIONS preflight requests from frontend frameworks must be accepted."""
    origin = "http://localhost:3000"
    response = client.options(
        "/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin
    assert "POST" in response.headers.get("access-control-allow-methods", "")


def test_list_user_evaluations(client, context):
    """GET /evaluations retrieves all evaluations owned by the authenticated user."""
    response = client.get(
        "/evaluations",
        headers=context["headers"],
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    eval_ids = [item["id"] for item in data]
    assert str(context["evaluation"].id) in eval_ids


def test_get_evaluation_detail(client, context):
    """GET /evaluations/detail/{evaluation_id} retrieves complete evaluation details."""
    eval_id = str(context["evaluation"].id)
    response = client.get(
        f"/evaluations/detail/{eval_id}",
        headers=context["headers"],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == eval_id
    assert "total_runs" in data
    assert "passed_runs" in data
    assert "average_latency_ms" in data


def test_get_evaluation_detail_not_found(client, context):
    """GET /evaluations/detail/{unknown_id} returns 404 Not Found."""
    unknown_id = str(uuid.uuid4())
    response = client.get(
        f"/evaluations/detail/{unknown_id}",
        headers=context["headers"],
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Evaluation not found"


def test_get_test_case_detail(client, context):
    """GET /test-cases/{test_case_id} retrieves a single test case detail."""
    tc_id = str(context["test_case"].id)
    response = client.get(
        f"/test-cases/{tc_id}",
        headers=context["headers"],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == tc_id
    assert data["evaluation_id"] == str(context["evaluation"].id)


def test_get_test_case_detail_not_found(client, context):
    """GET /test-cases/{unknown_id} returns 404 Not Found."""
    unknown_id = str(uuid.uuid4())
    response = client.get(
        f"/test-cases/{unknown_id}",
        headers=context["headers"],
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Test case not found"


def test_get_agent_version_detail(client, context):
    """GET /agent-versions/{version_id} retrieves a single agent version detail."""
    version_id = str(context["agent_version"].id)
    response = client.get(
        f"/agent-versions/{version_id}",
        headers=context["headers"],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == version_id
    assert "version" in data


def test_get_agent_version_detail_not_found(client, context):
    """GET /agent-versions/{unknown_id} returns 404 Not Found."""
    unknown_id = str(uuid.uuid4())
    response = client.get(
        f"/agent-versions/{unknown_id}",
        headers=context["headers"],
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Agent version not found"


def test_create_test_run_direct_via_body(client, context):
    """POST /test-runs directly executes a test run using JSON body with test_case_id."""
    tc_id = str(context["test_case"].id)
    response = client.post(
        "/test-runs",
        json={"test_case_id": tc_id},
        headers=context["headers"],
    )
    assert response.status_code == 201
    data = response.json()
    assert data["test_case_id"] == tc_id
    assert data["status"] in ["completed", "failed", "running"]
    assert "id" in data


def test_create_deployment_gate_with_overall_score(client, context, db_session):
    """Creating a deployment gate for an evaluation with overall_score computes the decision."""
    evaluation = context["evaluation"]
    original_score = evaluation.overall_score
    try:
        evaluation.overall_score = 0.92
        db_session.commit()

        response = client.post(
            f"/evaluations/{evaluation.id}/deployment-gate",
            headers=context["headers"],
        )
        assert response.status_code == 201
        data = response.json()
        assert data["decision"] == "PASS"
        assert data["overall_score"] == 0.92
        assert "meets the deployment threshold" in data["reason"]
    finally:
        evaluation.overall_score = original_score
        db_session.commit()
