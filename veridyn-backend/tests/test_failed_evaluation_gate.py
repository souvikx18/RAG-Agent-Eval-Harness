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
from app.models.deployment_gate import DeploymentGate


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


def test_failed_evaluation_deployment_gate(client, auth_headers, db_session):
    """
    Verifies that a failed agent evaluation completes with overall_score = 0.0,
    produces a Deployment Gate with BLOCK decision, and persists idempotently.
    """
    user = db_session.query(User).filter(User.email == "test2@example.com").first()
    agent = db_session.query(Agent).filter(Agent.owner_id == user.id).first()
    assert agent is not None

    agent_version = (
        db_session.query(AgentVersion)
        .filter(
            AgentVersion.agent_id == agent.id,
            AgentVersion.endpoint == "http://127.0.0.1:9999/agent",
        )
        .first()
    )
    assert agent_version is not None

    evaluation = (
        db_session.query(Evaluation)
        .filter(Evaluation.agent_version_id == agent_version.id)
        .first()
    )
    assert evaluation is not None

    # 1. Verify / list evaluation for this agent version
    eval_resp = client.get(f"/evaluations/{agent_version.id}", headers=auth_headers)
    assert eval_resp.status_code == 200
    eval_list = eval_resp.json()
    matched_eval = next((e for e in eval_list if e["id"] == str(evaluation.id)), None)
    assert matched_eval is not None
    assert matched_eval["status"] == "completed"
    assert matched_eval["overall_score"] == 0.0

    # 2. Verify Deployment Gate
    gate_resp = client.get(f"/evaluations/{evaluation.id}/deployment-gate", headers=auth_headers)
    assert gate_resp.status_code == 200
    gates = gate_resp.json()
    assert isinstance(gates, list)
    assert len(gates) >= 1

    primary_gate = gates[0]
    assert primary_gate["decision"] == "BLOCK"
    assert primary_gate["overall_score"] == 0.0
    assert "below the deployment threshold" in primary_gate["reason"]

    # 3. Verify persistence (subsequent calls return same gate without duplication)
    gate_resp_repeat = client.get(f"/evaluations/{evaluation.id}/deployment-gate", headers=auth_headers)
    assert gate_resp_repeat.status_code == 200
    gates_repeat = gate_resp_repeat.json()
    assert len(gates_repeat) == len(gates)
    assert gates_repeat[0]["id"] == primary_gate["id"]
