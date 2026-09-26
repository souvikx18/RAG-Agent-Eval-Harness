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
    Executes a TestRun against the live local agent on port 9000,
    validating output fidelity, status transitions, and metric calculations.
    """
    # 1. Retrieve or locate an active agent owned by the user
    user = db_session.query(User).filter(User.email == "test2@example.com").first()
    agent = db_session.query(Agent).filter(Agent.owner_id == user.id).first()
    assert agent is not None

    # 2. Verify agent version pointing to the local test agent
    agent_version = (
        db_session.query(AgentVersion)
        .filter(
            AgentVersion.agent_id == agent.id,
            AgentVersion.endpoint == "http://127.0.0.1:9000/agent",
        )
        .first()
    )
    assert agent_version is not None, "AgentVersion with http://127.0.0.1:9000/agent must exist"

    # 3. Locate an evaluation for this version
    evaluation = (
        db_session.query(Evaluation)
        .filter(Evaluation.agent_version_id == agent_version.id)
        .first()
    )
    assert evaluation is not None

    # 4. Locate TestCase
    test_case = (
        db_session.query(TestCase)
        .filter(TestCase.evaluation_id == evaluation.id)
        .first()
    )
    assert test_case is not None

    # 5. Execute TestRun
    run_resp = client.post(f"/test-cases/{test_case.id}/runs", headers=auth_headers)
    assert run_resp.status_code == 201
    run_data = run_resp.json()
    assert run_data["status"] == "completed"
    assert run_data["result"] == "passed"
    assert "Hello! I received your message:" in run_data["actual_output"]
    assert run_data["error_message"] is None

    # 6. Verify Evaluation Results
    results_resp = client.get(f"/test-runs/{run_data['id']}/results", headers=auth_headers)
    assert results_resp.status_code == 200
    results = results_resp.json()
    metrics = {r["metric_name"]: r for r in results}
    assert "correctness" in metrics
    assert metrics["correctness"]["score"] == 1.0
    assert metrics["correctness"]["status"] == "passed"
