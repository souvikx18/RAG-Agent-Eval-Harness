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


def test_get_test_run_detail_own_test_run(client, authenticated_context, db_session):
    """
    TestRun Detail API Contract Test (Step 164):
    Call GET /test-runs/{YOUR_TEST_RUN_ID}
    Expected: 200 OK with execution metadata
    """
    test_case_id = authenticated_context["own_test_case_id"]
    headers = authenticated_context["headers"]

    # First fetch list to find or create a test run
    runs_resp = client.get(f"/test-cases/{test_case_id}/runs", headers=headers)
    assert runs_resp.status_code == 200
    runs = runs_resp.json()

    if not runs:
        # Create a run if none exists
        create_resp = client.post(f"/test-cases/{test_case_id}/runs", headers=headers)
        assert create_resp.status_code == 201
        run_id = create_resp.json()["id"]
    else:
        run_id = runs[0]["id"]

    response = client.get(f"/test-runs/{run_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()

    # Core contract fields
    assert "id" in data
    assert "test_case_id" in data
    assert "status" in data
    assert "actual_output" in data
    assert "latency_ms" in data
    assert "started_at" in data
    assert "completed_at" in data
    assert "executor_type" in data

    # Execution metadata contract
    assert data["started_at"] is not None
    assert data["completed_at"] is not None
    assert data["executor_type"] is not None
    assert data["latency_ms"] is not None
    assert data["latency_ms"] >= 0


def test_get_test_run_detail_unknown(client, authenticated_context):
    unknown_id = "00000000-0000-0000-0000-000000000001"
    headers = authenticated_context["headers"]
    response = client.get(f"/test-runs/{unknown_id}", headers=headers)
    assert response.status_code == 404
    assert response.json().get("detail") == "Test run not found"


def test_get_test_run_detail_missing_jwt(client, authenticated_context, db_session):
    test_case_id = authenticated_context["own_test_case_id"]
    headers = authenticated_context["headers"]
    runs_resp = client.get(f"/test-cases/{test_case_id}/runs", headers=headers)
    assert runs_resp.status_code == 200
    runs = runs_resp.json()
    if runs:
        run_id = runs[0]["id"]
        response = client.get(f"/test-runs/{run_id}")
        assert response.status_code == 401


def test_list_test_runs_includes_execution_metadata(client, authenticated_context):
    test_case_id = authenticated_context["own_test_case_id"]
    headers = authenticated_context["headers"]

    response = client.get(f"/test-cases/{test_case_id}/runs", headers=headers)
    assert response.status_code == 200
    runs = response.json()
    for run in runs:
        assert "started_at" in run
        assert "completed_at" in run
        assert "executor_type" in run
        assert "latency_ms" in run


def test_test_run_api_metadata_regression_coverage(client, authenticated_context, db_session):
    """
    Step 167: Verify TestRun API response contract regression coverage
    for established fields across execution outcomes.
    """
    headers = authenticated_context["headers"]
    user = authenticated_context["user"]

    # 1. Query for existing HTTP test case
    agent_version = (
        db_session.query(AgentVersion)
        .join(Agent, AgentVersion.agent_id == Agent.id)
        .filter(
            Agent.owner_id == user.id,
            AgentVersion.endpoint == "http://127.0.0.1:9000/agent",
        )
        .first()
    )

    if agent_version:
        evaluation = (
            db_session.query(Evaluation)
            .filter(Evaluation.agent_version_id == agent_version.id)
            .first()
        )
        test_case = (
            db_session.query(TestCase)
            .filter(TestCase.evaluation_id == evaluation.id)
            .first()
        )
        if test_case:
            resp = client.get(f"/test-cases/{test_case.id}/runs", headers=headers)
            assert resp.status_code == 200
            runs = resp.json()
            for data in runs:
                assert "started_at" in data
                assert "executor_type" in data
                assert "completed_at" in data
                assert "latency_ms" in data

                if data.get("executor_type") == "HTTPAgentExecutor":
                    assert data["executor_type"] == "HTTPAgentExecutor"
                    assert data["started_at"] is not None
                    assert data["completed_at"] is not None
                    assert data["latency_ms"] is not None
                    assert data["latency_ms"] >= 0


def test_list_test_runs_pagination_and_filtering(client, authenticated_context, db_session):
    """
    Step 169: Verify pagination and status filtering on TestRun list endpoints:
    - Default pagination
    - Custom skip and limit
    - Maximum limit enforcement (limit <= 100)
    - Invalid pagination values (skip < 0, limit < 1)
    - Status filtering (pending, running, completed, failed)
    - Invalid status value rejection (422)
    - Empty result sets
    - Stable ordering
    - Support for both /test-cases/{id}/runs and /test-runs
    """
    test_case_id = authenticated_context["own_test_case_id"]
    headers = authenticated_context["headers"]

    # Seed multiple test runs with distinct statuses, timestamps, and metadata to test pagination & filtering
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    seeded_ids = []
    for i in range(5):
        run = TestRun(
            id=uuid.uuid4(),
            test_case_id=uuid.UUID(test_case_id),
            status="completed" if i % 2 == 0 else "failed",
            actual_output=f"Output {i}",
            latency_ms=100 + i,
            started_at=now,
            completed_at=now,
            executor_type="HTTPAgentExecutor",
        )
        db_session.add(run)
        seeded_ids.append(run.id)
    db_session.commit()

    try:
        # 1. Default pagination
        resp = client.get(f"/test-cases/{test_case_id}/runs", headers=headers)
        assert resp.status_code == 200
        all_runs = resp.json()
        assert len(all_runs) >= 5

        # 2. Custom skip and limit
        resp_limit = client.get(f"/test-cases/{test_case_id}/runs?skip=0&limit=2", headers=headers)
        assert resp_limit.status_code == 200
        page_1 = resp_limit.json()
        assert len(page_1) == 2

        resp_skip = client.get(f"/test-cases/{test_case_id}/runs?skip=2&limit=2", headers=headers)
        assert resp_skip.status_code == 200
        page_2 = resp_skip.json()
        assert len(page_2) == 2

        # Stable ordering: page 1 and page 2 must not intersect
        page_1_ids = {r["id"] for r in page_1}
        page_2_ids = {r["id"] for r in page_2}
        assert page_1_ids.isdisjoint(page_2_ids)

        # 3. Maximum limit enforcement (le=100)
        resp_over_limit = client.get(f"/test-cases/{test_case_id}/runs?limit=101", headers=headers)
        assert resp_over_limit.status_code == 422

        # 4. Invalid pagination values
        resp_neg_skip = client.get(f"/test-cases/{test_case_id}/runs?skip=-1", headers=headers)
        assert resp_neg_skip.status_code == 422

        resp_zero_limit = client.get(f"/test-cases/{test_case_id}/runs?limit=0", headers=headers)
        assert resp_zero_limit.status_code == 422

        # 5. Status filtering
        resp_completed = client.get(f"/test-cases/{test_case_id}/runs?status=completed", headers=headers)
        assert resp_completed.status_code == 200
        completed_runs = resp_completed.json()
        assert len(completed_runs) > 0
        assert all(r["status"] == "completed" for r in completed_runs)

        resp_failed = client.get(f"/test-cases/{test_case_id}/runs?status=failed", headers=headers)
        assert resp_failed.status_code == 200
        failed_runs = resp_failed.json()
        assert len(failed_runs) > 0
        assert all(r["status"] == "failed" for r in failed_runs)

        # 6. Invalid status filter
        resp_invalid_status = client.get(f"/test-cases/{test_case_id}/runs?status=nonexistent", headers=headers)
        assert resp_invalid_status.status_code == 422

        # 7. Empty result set (e.g., status that has no runs in this test case or high skip)
        resp_empty = client.get(f"/test-cases/{test_case_id}/runs?skip=1000", headers=headers)
        assert resp_empty.status_code == 200
        assert resp_empty.json() == []

        # 8. Test /test-runs endpoint pagination and filtering
        resp_all_runs = client.get("/test-runs?limit=3", headers=headers)
        assert resp_all_runs.status_code == 200
        data_all = resp_all_runs.json()
        assert len(data_all) <= 3

        resp_all_status = client.get("/test-runs?status=completed&limit=10", headers=headers)
        assert resp_all_status.status_code == 200
        assert all(r["status"] == "completed" for r in resp_all_status.json())

        resp_all_invalid = client.get("/test-runs?status=invalid_status", headers=headers)
        assert resp_all_invalid.status_code == 422
    finally:
        db_session.query(TestRun).filter(TestRun.id.in_(seeded_ids)).delete(synchronize_session=False)
        db_session.commit()


def test_list_test_runs_pagination_metadata(client, authenticated_context, db_session):
    """
    Step 170: Verify TestRun pagination metadata envelope and headers:
    - Empty datasets (total=0, items=[], has_more=False)
    - First page and subsequent pages
    - Final partial page
    - Status-filtered totals
    - has_more when more records exist (True)
    - has_more when no additional records exist (False)
    - Consistent totals, skip, limit, and items structure
    - Both /test-cases/{id}/runs and /test-runs endpoints
    """
    test_case_id = authenticated_context["own_test_case_id"]
    headers = authenticated_context["headers"]

    # 1. Empty dataset test: query nonexistent test case with pagination
    # (Or use an owned test case with a filter matching 0 items)
    resp_empty = client.get(
        f"/test-cases/{test_case_id}/runs?status=pending&paginated=true",
        headers=headers,
    )
    assert resp_empty.status_code == 200
    meta_empty = resp_empty.json()
    assert meta_empty["items"] == []
    assert meta_empty["total"] == 0
    assert meta_empty["skip"] == 0
    assert meta_empty["has_more"] is False

    # Seed 7 test runs for controlled pagination testing: 4 completed, 3 failed
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    seeded_ids = []
    for i in range(7):
        status_val = "completed" if i < 4 else "failed"
        run = TestRun(
            id=uuid.uuid4(),
            test_case_id=uuid.UUID(test_case_id),
            status=status_val,
            actual_output=f"Pagination meta output {i}",
            latency_ms=50 + i,
            started_at=now,
            completed_at=now,
            executor_type="HTTPAgentExecutor",
        )
        db_session.add(run)
        seeded_ids.append(run.id)
    db_session.commit()

    try:
        # 2. First page with paginated=true (limit=3) -> more records exist
        resp_p1 = client.get(
            f"/test-cases/{test_case_id}/runs?skip=0&limit=3&paginated=true",
            headers=headers,
        )
        assert resp_p1.status_code == 200
        p1 = resp_p1.json()
        assert p1["skip"] == 0
        assert p1["limit"] == 3
        assert len(p1["items"]) == 3
        assert p1["total"] >= 7
        assert p1["has_more"] is True

        # Check pagination headers
        assert "X-Total-Count" in resp_p1.headers
        assert int(resp_p1.headers["X-Total-Count"]) == p1["total"]
        assert resp_p1.headers["X-Has-More"] == "true"

        # 3. Subsequent page (skip=3, limit=3)
        resp_p2 = client.get(
            f"/test-cases/{test_case_id}/runs?skip=3&limit=3&paginated=true",
            headers=headers,
        )
        assert resp_p2.status_code == 200
        p2 = resp_p2.json()
        assert p2["skip"] == 3
        assert p2["limit"] == 3
        assert len(p2["items"]) == 3
        assert p2["total"] == p1["total"]

        # 4. Final page / beyond end -> has_more is False
        resp_p_end = client.get(
            f"/test-cases/{test_case_id}/runs?skip={p1['total']}&limit=10&paginated=true",
            headers=headers,
        )
        assert resp_p_end.status_code == 200
        p_end = resp_p_end.json()
        assert p_end["items"] == []
        assert p_end["total"] == p1["total"]
        assert p_end["has_more"] is False
        assert resp_p_end.headers["X-Has-More"] == "false"

        # 5. Status-filtered totals (status=failed, skip=0, limit=2)
        resp_filtered = client.get(
            f"/test-cases/{test_case_id}/runs?status=failed&skip=0&limit=2&paginated=true",
            headers=headers,
        )
        assert resp_filtered.status_code == 200
        filtered_meta = resp_filtered.json()
        assert filtered_meta["total"] >= 3
        assert len(filtered_meta["items"]) == 2
        assert all(item["status"] == "failed" for item in filtered_meta["items"])
        assert filtered_meta["has_more"] is True

        # Final partial page for status=failed (skip=2, limit=2)
        resp_failed_p2 = client.get(
            f"/test-cases/{test_case_id}/runs?status=failed&skip=2&limit=2&paginated=true",
            headers=headers,
        )
        assert resp_failed_p2.status_code == 200
        meta_failed_p2 = resp_failed_p2.json()
        assert len(meta_failed_p2["items"]) >= 1
        assert meta_failed_p2["total"] == filtered_meta["total"]

        # 6. Global /test-runs endpoint with paginated metadata
        resp_global = client.get("/test-runs?skip=0&limit=5&paginated=true", headers=headers)
        assert resp_global.status_code == 200
        global_data = resp_global.json()
        assert "items" in global_data
        assert "total" in global_data
        assert "skip" in global_data
        assert "limit" in global_data
        assert "has_more" in global_data
        assert global_data["total"] >= 7
    finally:
        db_session.query(TestRun).filter(TestRun.id.in_(seeded_ids)).delete(synchronize_session=False)
        db_session.commit()



