from unittest.mock import patch, MagicMock
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
from app.models.evaluation_result import EvaluationResult


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="module")
def auth_headers(db_session):
    user = db_session.query(User).filter(User.email == "test2@example.com").first()
    assert user is not None, "Authenticated test user required"
    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}


def test_http_agent_e2e_integration(client, auth_headers, db_session):
    """
    Step 77 End-to-End Integration Test:
    Executes a TestRun against the agent endpoint,
    validating output fidelity, status transitions, and metric calculations.
    """
    user = db_session.query(User).filter(User.email == "test2@example.com").first()
    agent = db_session.query(Agent).filter(Agent.owner_id == user.id).first()
    assert agent is not None

    agent_version = (
        db_session.query(AgentVersion)
        .filter(
            AgentVersion.agent_id == agent.id,
            AgentVersion.endpoint == "http://127.0.0.1:9000/agent",
        )
        .first()
    )
    assert agent_version is not None, "AgentVersion with http://127.0.0.1:9000/agent must exist"

    evaluation = (
        db_session.query(Evaluation)
        .filter(Evaluation.agent_version_id == agent_version.id)
        .first()
    )
    assert evaluation is not None

    test_case = (
        db_session.query(TestCase)
        .filter(TestCase.evaluation_id == evaluation.id)
        .first()
    )
    assert test_case is not None

    # Mock the HTTP agent response for reliable, isolated CI/CD testing
    with patch("httpx.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "output": f"Hello! I received your message: {test_case.expected_behavior}"
            if test_case.expected_behavior
            else "Hello! I received your message: Hello Veridyn"
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Execute TestRun
        run_resp = client.post(f"/test-cases/{test_case.id}/runs", headers=auth_headers)
        assert run_resp.status_code == 201
        run_data = run_resp.json()
        assert run_data["status"] == "completed"
        assert run_data["result"] == "passed"
        assert "Hello! I received your message:" in run_data["actual_output"]
        assert run_resp.json()["started_at"] is not None
        assert run_resp.json()["executor_type"] == "HTTPAgentExecutor"

    # Verify TestRun Detail API contract (Step 164)
    detail_resp = client.get(f"/test-runs/{run_data['id']}", headers=auth_headers)
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()

    assert detail_data["started_at"] is not None
    assert detail_data["executor_type"] == "HTTPAgentExecutor"
    assert detail_data["completed_at"] is not None
    assert detail_data["latency_ms"] is not None
    assert detail_data["latency_ms"] >= 0

    # Verify established response contract fields are preserved
    assert "id" in detail_data
    assert "test_case_id" in detail_data
    assert "status" in detail_data
    assert "actual_output" in detail_data
    assert "completed_at" in detail_data
    assert "latency_ms" in detail_data
    assert "started_at" in detail_data
    assert "executor_type" in detail_data

    # Verify Evaluation Results
    results_resp = client.get(f"/test-runs/{run_data['id']}/results", headers=auth_headers)
    assert results_resp.status_code == 200
    results = results_resp.json()
    metrics = {r["metric_name"]: r for r in results}
    assert "correctness" in metrics
    assert metrics["correctness"]["score"] == 1.0
    assert metrics["correctness"]["status"] == "passed"
