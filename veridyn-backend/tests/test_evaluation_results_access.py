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


def test_evaluation_result_api_returns_configuration_metadata(client, authenticated_context):
    test_run_id = authenticated_context["own_test_run_id"]
    headers = authenticated_context["headers"]
    payload = {
        "metric_name": "correctness",
        "score": 1.0,
        "status": "passed",
        "explanation": "Testing configuration metadata in API response",
        "configuration_version": 2,
        "configuration": {
            "case_sensitive": True,
        },
    }

    response = client.post(
        f"/test-runs/{test_run_id}/results",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["configuration_version"] == 2
    assert response.json()["configuration"] == {
        "case_sensitive": True,
    }

    # Also verify GET returns the configuration metadata
    get_response = client.get(
        f"/test-runs/{test_run_id}/results",
        headers=headers,
    )
    assert get_response.status_code == 200
    matching = next(
        r for r in get_response.json() if r["configuration_version"] == 2
    )
    assert matching["configuration"] == {
        "case_sensitive": True,
    }


def test_evaluation_result_api_serialization_contract(client, authenticated_context):
    test_run_id = authenticated_context["own_test_run_id"]
    headers = authenticated_context["headers"]
    payload = {
        "metric_name": "correctness",
        "score": 1.0,
        "status": "passed",
        "explanation": "Testing configuration serialization contract",
        "configuration_version": 2,
        "configuration": {
            "case_sensitive": True,
        },
    }

    response = client.post(
        f"/test-runs/{test_run_id}/results",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()

    assert "metric_name" in data
    assert "score" in data
    assert "status" in data
    assert "explanation" in data
    assert "configuration_version" in data
    assert "configuration" in data

    assert data["metric_name"] == "correctness"
    assert data["score"] == 1.0
    assert data["status"] == "passed"
    assert data["explanation"] == "Testing configuration serialization contract"
    assert data["configuration_version"] == 2
    assert data["configuration"] == {
        "case_sensitive": True,
    }


def test_evaluation_result_api_configuration_version_contract(client, authenticated_context):
    from app.services.metrics.registry import metric_registry

    test_run_id = authenticated_context["own_test_run_id"]
    headers = authenticated_context["headers"]

    payload = {
        "metric_name": "correctness",
        "score": 1.0,
        "status": "passed",
        "explanation": "Version contract verification",
        "configuration_version": 2,
        "configuration": {
            "case_sensitive": True,
        },
    }

    response = client.post(
        f"/test-runs/{test_run_id}/results",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["configuration_version"] >= 1
    assert response.json()["configuration_version"] == 2
    assert response.json()["configuration"] == {
        "case_sensitive": True,
    }

    # Verify that changing current metric registry configuration cannot alter historical persisted version
    metric_registry.configure("correctness", {"case_sensitive": False})

    try:
        get_response = client.get(
            f"/test-runs/{test_run_id}/results",
            headers=headers,
        )
        assert get_response.status_code == 200
        matching = next(
            r for r in get_response.json()
            if r["explanation"] == "Version contract verification"
        )
        assert matching["configuration_version"] >= 1
        assert matching["configuration_version"] == 2
        assert matching["configuration"] == {
            "case_sensitive": True,
        }
    finally:
        metric_registry.reset()


def test_metric_evaluation_api_integration_and_contract_validation(client, authenticated_context, db_session):
    """
    Step 183: Metric Evaluation API Integration & Contract Validation.
    - Validates the end-to-end flow from API submission to response serialization and persistence.
    - Tests successful metric evaluation result creation via API.
    - Validates contract schema: score, status, explanation, configuration_version, configuration.
    - Tests input validation errors (HTTP 422 for missing required fields, empty strings, invalid types).
    - Verifies association with parent TestRun.
    - Confirms persisted database records exactly match the API serialization response.
    """
    test_run_id = authenticated_context["own_test_run_id"]
    headers = authenticated_context["headers"]

    # 1. Successful creation through API with full contract
    valid_payload = {
        "metric_name": "custom_contract_metric",
        "score": 0.85,
        "status": "passed",
        "explanation": "Agent response adhered to custom evaluation criteria",
        "configuration_version": 3,
        "configuration": {
            "strict_mode": True,
            "threshold": 0.8,
        },
    }

    create_resp = client.post(
        f"/test-runs/{test_run_id}/results",
        json=valid_payload,
        headers=headers,
    )
    assert create_resp.status_code == 201
    created_data = create_resp.json()

    # Validate response schema
    assert "id" in created_data
    assert created_data["test_run_id"] == test_run_id
    assert created_data["metric_name"] == "custom_contract_metric"
    assert created_data["score"] == 0.85
    assert created_data["status"] == "passed"
    assert created_data["explanation"] == "Agent response adhered to custom evaluation criteria"
    assert created_data["configuration_version"] == 3
    assert created_data["configuration"] == {
        "strict_mode": True,
        "threshold": 0.8,
    }

    # 2. Verify persisted record in DB matches API response
    result_id = uuid.UUID(created_data["id"])
    db_record = db_session.query(EvaluationResult).filter(EvaluationResult.id == result_id).first()
    assert db_record is not None
    assert str(db_record.test_run_id) == test_run_id
    assert db_record.metric_name == valid_payload["metric_name"]
    assert db_record.score == valid_payload["score"]
    assert db_record.status == valid_payload["status"]
    assert db_record.explanation == valid_payload["explanation"]
    assert db_record.configuration_version == valid_payload["configuration_version"]
    assert db_record.configuration == valid_payload["configuration"]

    # 3. Test list endpoint retrieval
    list_resp = client.get(f"/test-runs/{test_run_id}/results", headers=headers)
    assert list_resp.status_code == 200
    all_results = list_resp.json()
    matched = next((r for r in all_results if r["id"] == str(result_id)), None)
    assert matched is not None
    assert matched["metric_name"] == "custom_contract_metric"
    assert matched["score"] == 0.85
    assert matched["configuration_version"] == 3
    assert matched["configuration"] == {"strict_mode": True, "threshold": 0.8}

    # 4. Input validation: missing required field (status) -> HTTP 422
    invalid_missing_status = {
        "metric_name": "incomplete_metric",
        "score": 0.5,
    }
    resp_missing = client.post(
        f"/test-runs/{test_run_id}/results",
        json=invalid_missing_status,
        headers=headers,
    )
    assert resp_missing.status_code == 422

    # 5. Input validation: empty metric_name -> HTTP 422
    invalid_empty_metric = {
        "metric_name": "",
        "status": "passed",
    }
    resp_empty = client.post(
        f"/test-runs/{test_run_id}/results",
        json=invalid_empty_metric,
        headers=headers,
    )
    assert resp_empty.status_code == 422

    # 6. Input validation: malformed JSON / non-dict configuration -> HTTP 422
    invalid_config_type = {
        "metric_name": "bad_config",
        "status": "passed",
        "configuration": "not-a-dictionary",
    }
    resp_bad_config = client.post(
        f"/test-runs/{test_run_id}/results",
        json=invalid_config_type,
        headers=headers,
    )
    assert resp_bad_config.status_code == 422

    # Clean up test result
    db_session.query(EvaluationResult).filter(EvaluationResult.id == result_id).delete(synchronize_session=False)
    db_session.commit()




