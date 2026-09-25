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
def full_lineage_context(db_session):
    user = db_session.query(User).first()
    assert user is not None, "A user is required for full chain testing"
    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    # Find a test run that belongs to this user through the full chain
    test_run = (
        db_session.query(TestRun)
        .join(TestCase, TestRun.test_case_id == TestCase.id)
        .join(Evaluation, TestCase.evaluation_id == Evaluation.id)
        .join(AgentVersion, Evaluation.agent_version_id == AgentVersion.id)
        .join(Agent, AgentVersion.agent_id == Agent.id)
        .filter(Agent.owner_id == user.id)
        .first()
    )
    assert test_run is not None, "User must have an active TestRun in the chain"

    test_case = db_session.query(TestCase).filter(TestCase.id == test_run.test_case_id).first()
    evaluation = db_session.query(Evaluation).filter(Evaluation.id == test_case.evaluation_id).first()
    agent_version = db_session.query(AgentVersion).filter(AgentVersion.id == evaluation.agent_version_id).first()
    agent = db_session.query(Agent).filter(Agent.id == agent_version.agent_id).first()

    return {
        "user": user,
        "token": token,
        "headers": headers,
        "agent_id": str(agent.id),
        "agent_version_id": str(agent_version.id),
        "evaluation_id": str(evaluation.id),
        "test_case_id": str(test_case.id),
        "test_run_id": str(test_run.id),
    }


def test_chain_step_1_agents(client, full_lineage_context):
    """Test 1 — Agents: GET /agents -> 200 OK (only owned agents)."""
    resp = client.get("/agents", headers=full_lineage_context["headers"])
    assert resp.status_code == 200
    agents = resp.json()
    assert isinstance(agents, list)
    assert any(a["id"] == full_lineage_context["agent_id"] for a in agents)


def test_chain_step_2_agent_versions(client, full_lineage_context):
    """Test 2 — Agent Versions: GET /agents/{YOUR_AGENT_ID}/versions -> 200 OK."""
    agent_id = full_lineage_context["agent_id"]
    resp = client.get(f"/agents/{agent_id}/versions", headers=full_lineage_context["headers"])
    assert resp.status_code == 200
    versions = resp.json()
    assert isinstance(versions, list)
    assert any(v["id"] == full_lineage_context["agent_version_id"] for v in versions)


def test_chain_step_3_evaluations(client, full_lineage_context):
    """Test 3 — Evaluations: GET /evaluations/{YOUR_AGENT_VERSION_ID} -> 200 OK."""
    agent_version_id = full_lineage_context["agent_version_id"]
    resp = client.get(f"/evaluations/{agent_version_id}", headers=full_lineage_context["headers"])
    assert resp.status_code == 200
    evals = resp.json()
    assert isinstance(evals, list)
    assert any(e["id"] == full_lineage_context["evaluation_id"] for e in evals)


def test_chain_step_4_test_cases(client, full_lineage_context):
    """Test 4 — TestCases: GET /evaluations/{YOUR_EVALUATION_ID}/test-cases -> 200 OK."""
    eval_id = full_lineage_context["evaluation_id"]
    resp = client.get(f"/evaluations/{eval_id}/test-cases", headers=full_lineage_context["headers"])
    assert resp.status_code == 200
    test_cases = resp.json()
    assert isinstance(test_cases, list)
    assert any(tc["id"] == full_lineage_context["test_case_id"] for tc in test_cases)


def test_chain_step_5_test_runs(client, full_lineage_context):
    """Test 5 — TestRuns: GET /test-cases/{YOUR_TEST_CASE_ID}/runs -> 200 OK."""
    tc_id = full_lineage_context["test_case_id"]
    resp = client.get(f"/test-cases/{tc_id}/runs", headers=full_lineage_context["headers"])
    assert resp.status_code == 200
    runs = resp.json()
    assert isinstance(runs, list)
    assert any(r["id"] == full_lineage_context["test_run_id"] for r in runs)


def test_chain_step_6_traces(client, full_lineage_context):
    """Test 6 — Traces: GET /test-runs/{YOUR_TEST_RUN_ID}/traces -> 200 OK."""
    tr_id = full_lineage_context["test_run_id"]
    resp = client.get(f"/test-runs/{tr_id}/traces", headers=full_lineage_context["headers"])
    assert resp.status_code == 200
    traces = resp.json()
    assert isinstance(traces, list)


def test_chain_step_7_results(client, full_lineage_context):
    """Test 7 — Results: GET /test-runs/{YOUR_TEST_RUN_ID}/results -> 200 OK."""
    tr_id = full_lineage_context["test_run_id"]
    resp = client.get(f"/test-runs/{tr_id}/results", headers=full_lineage_context["headers"])
    assert resp.status_code == 200
    results = resp.json()
    assert isinstance(results, list)


def test_chain_step_8_deployment_gate(client, full_lineage_context):
    """Test 8 — Deployment Gate: GET /evaluations/{YOUR_EVALUATION_ID}/deployment-gate -> 200 OK."""
    eval_id = full_lineage_context["evaluation_id"]
    resp = client.get(f"/evaluations/{eval_id}/deployment-gate", headers=full_lineage_context["headers"])
    assert resp.status_code == 200
    gates = resp.json()
    assert isinstance(gates, list)


def test_chain_invalid_ids_return_404(client, full_lineage_context):
    """
    Final security check:
    Verify that an invalid ID (00000000-0000-0000-0000-000000000001) at each level returns 404.
    """
    invalid_id = "00000000-0000-0000-0000-000000000001"
    headers = full_lineage_context["headers"]

    endpoints = [
        f"/agents/{invalid_id}/versions",
        f"/evaluations/{invalid_id}",
        f"/evaluations/{invalid_id}/test-cases",
        f"/test-cases/{invalid_id}/runs",
        f"/test-runs/{invalid_id}/traces",
        f"/test-runs/{invalid_id}/results",
        f"/evaluations/{invalid_id}/deployment-gate",
    ]

    for endpoint in endpoints:
        resp = client.get(endpoint, headers=headers)
        assert resp.status_code == 404, f"Expected 404 for {endpoint}, got {resp.status_code}"
