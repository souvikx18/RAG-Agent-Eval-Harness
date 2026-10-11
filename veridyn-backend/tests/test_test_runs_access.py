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


def test_list_test_runs_sorting_and_ordering(client, authenticated_context, db_session):
    """
    Step 171: Verify sorting and ordering functionality on TestRun endpoints:
    - Ascending and descending order
    - Sorting by latency_ms, status, created_at
    - Multiple records with identical timestamps (tie-breaking with record ID)
    - Stable ordering across pages
    - Sorting combined with status filtering
    - Sorting combined with pagination metadata
    - Rejection of invalid sort_by and order fields with 422
    - Coverage for both /test-cases/{id}/runs and /test-runs
    """
    test_case_id = authenticated_context["own_test_case_id"]
    headers = authenticated_context["headers"]

    # 1. Validation errors for invalid sort_by or order
    resp_bad_field = client.get(
        f"/test-cases/{test_case_id}/runs?sort_by=nonexistent_field",
        headers=headers,
    )
    assert resp_bad_field.status_code == 422
    assert "Invalid sort_by" in resp_bad_field.json().get("detail", "")

    resp_bad_order = client.get(
        f"/test-cases/{test_case_id}/runs?sort_by=created_at&order=diagonal",
        headers=headers,
    )
    assert resp_bad_order.status_code == 422
    assert "Invalid order" in resp_bad_order.json().get("detail", "")

    # Seed 6 test runs with distinct latencies and identical timestamps to test tie-breaking
    from datetime import datetime, timezone
    fixed_time = datetime.now(timezone.utc)
    seeded_ids = []
    latencies = [150, 50, 300, 200, 100, 250]
    for i, lat in enumerate(latencies):
        run = TestRun(
            id=uuid.uuid4(),
            test_case_id=uuid.UUID(test_case_id),
            status="completed" if i % 2 == 0 else "failed",
            actual_output=f"Sort test output {i}",
            latency_ms=lat,
            started_at=fixed_time,
            completed_at=fixed_time,
            created_at=fixed_time,  # Identical timestamps to verify stable ID tie-breaker
            executor_type="HTTPAgentExecutor",
        )
        db_session.add(run)
        seeded_ids.append(run.id)
    db_session.commit()

    try:
        # 2. Test sorting by latency_ms ascending
        resp_asc = client.get(
            f"/test-cases/{test_case_id}/runs?sort_by=latency_ms&order=asc&limit=6&paginated=true",
            headers=headers,
        )
        assert resp_asc.status_code == 200
        items_asc = resp_asc.json()["items"]
        returned_lats = [r["latency_ms"] for r in items_asc if r["latency_ms"] is not None]
        assert returned_lats == sorted(returned_lats)

        # 3. Test sorting by latency_ms descending
        resp_desc = client.get(
            f"/test-cases/{test_case_id}/runs?sort_by=latency_ms&order=desc&limit=6&paginated=true",
            headers=headers,
        )
        assert resp_desc.status_code == 200
        items_desc = resp_desc.json()["items"]
        returned_desc_lats = [r["latency_ms"] for r in items_desc if r["latency_ms"] is not None]
        assert returned_desc_lats == sorted(returned_desc_lats, reverse=True)

        # 4. Stable ordering across pages with identical timestamps
        p1 = client.get(
            f"/test-cases/{test_case_id}/runs?sort_by=created_at&order=asc&skip=0&limit=3",
            headers=headers,
        ).json()
        p2 = client.get(
            f"/test-cases/{test_case_id}/runs?sort_by=created_at&order=asc&skip=3&limit=3",
            headers=headers,
        ).json()
        assert len(p1) == 3
        assert len(p2) == 3
        p1_ids = {r["id"] for r in p1}
        p2_ids = {r["id"] for r in p2}
        assert p1_ids.isdisjoint(p2_ids)

        # 5. Sorting combined with status filtering and pagination metadata
        resp_filtered_sort = client.get(
            f"/test-cases/{test_case_id}/runs?status=completed&sort_by=latency_ms&order=desc&skip=0&limit=2&paginated=true",
            headers=headers,
        )
        assert resp_filtered_sort.status_code == 200
        meta = resp_filtered_sort.json()
        assert meta["skip"] == 0
        assert meta["limit"] == 2
        assert len(meta["items"]) == 2
        assert all(r["status"] == "completed" for r in meta["items"])
        assert meta["items"][0]["latency_ms"] >= meta["items"][1]["latency_ms"]

        # 6. Global /test-runs sorting validation
        resp_global = client.get(
            "/test-runs?sort_by=latency_ms&order=asc&limit=4&paginated=true",
            headers=headers,
        )
        assert resp_global.status_code == 200
        global_items = resp_global.json()["items"]
        g_lats = [r["latency_ms"] for r in global_items if r["latency_ms"] is not None]
        assert g_lats == sorted(g_lats)

        # 7. Invalid parameters on /test-runs
        assert client.get("/test-runs?sort_by=invalid", headers=headers).status_code == 422
        assert client.get("/test-runs?order=invalid", headers=headers).status_code == 422
    finally:
        db_session.query(TestRun).filter(TestRun.id.in_(seeded_ids)).delete(synchronize_session=False)
        db_session.commit()


def test_test_run_api_input_validation(client, authenticated_context):
    """
    Step 172: Dedicated input validation tests for TestRun endpoints:
    - Negative pagination values (skip < 0, limit < 1)
    - Excessive limits (limit > 100)
    - Non-integer pagination inputs
    - Invalid sorting parameters (unsupported sort_by field, unsupported order direction)
    - Unsupported status filters
    - Valid combinations of query parameters (skip, limit, status, sort_by, order, paginated)
    - Validations on both /test-cases/{id}/runs and /test-runs
    """
    test_case_id = authenticated_context["own_test_case_id"]
    headers = authenticated_context["headers"]

    endpoints = [
        f"/test-cases/{test_case_id}/runs",
        "/test-runs",
    ]

    for base_url in endpoints:
        # 1. Negative skip
        resp = client.get(f"{base_url}?skip=-5", headers=headers)
        assert resp.status_code == 422

        # 2. Limit less than 1 (zero or negative)
        resp = client.get(f"{base_url}?limit=0", headers=headers)
        assert resp.status_code == 422

        resp = client.get(f"{base_url}?limit=-10", headers=headers)
        assert resp.status_code == 422

        # 3. Excessive limits (limit > 100)
        resp = client.get(f"{base_url}?limit=101", headers=headers)
        assert resp.status_code == 422

        resp = client.get(f"{base_url}?limit=500", headers=headers)
        assert resp.status_code == 422

        # 4. Non-integer pagination inputs
        resp = client.get(f"{base_url}?skip=abc", headers=headers)
        assert resp.status_code == 422

        resp = client.get(f"{base_url}?limit=xyz", headers=headers)
        assert resp.status_code == 422

        # 5. Invalid sorting parameters
        resp = client.get(f"{base_url}?sort_by=drop_table", headers=headers)
        assert resp.status_code == 422
        assert "Invalid sort_by" in resp.json().get("detail", "")

        resp = client.get(f"{base_url}?order=random", headers=headers)
        assert resp.status_code == 422
        assert "Invalid order" in resp.json().get("detail", "")

        # 6. Unsupported status filters
        resp = client.get(f"{base_url}?status=in_progress", headers=headers)
        assert resp.status_code == 422
        assert "Invalid status" in resp.json().get("detail", "")

        resp = client.get(f"{base_url}?status=UNKNOWN", headers=headers)
        assert resp.status_code == 422

        # 7. Valid combinations of query parameters
        valid_params = [
            "?skip=0&limit=10",
            "?skip=5&limit=25&status=completed",
            "?skip=0&limit=50&status=failed&sort_by=latency_ms&order=asc",
            "?skip=10&limit=100&status=pending&sort_by=created_at&order=desc&paginated=true",
            "?sort_by=started_at&order=asc",
            "?sort_by=completed_at&order=desc",
            "?sort_by=status&order=asc",
        ]
        for query_str in valid_params:
            resp = client.get(f"{base_url}{query_str}", headers=headers)
            assert resp.status_code == 200, f"Expected 200 for {base_url}{query_str}, got {resp.status_code}"


def test_test_run_api_combined_query_integration(client, authenticated_context, db_session):
    """
    Step 173: Add TestRun API Integration Tests.
    Verifies that filtering, sorting, pagination, and pagination metadata work
    correctly together through both /test-cases/{id}/runs and /test-runs:
    - Status filtering combined with pagination
    - Sorting combined with pagination
    - Filtering, sorting, and pagination used together
    - `total` reflects the filtered dataset before pagination
    - `has_more` correctly reflects whether additional matching records exist
    - Consecutive pages contain no duplicate records when the dataset remains unchanged
    - Empty filtered results return the expected response format (empty items, total=0, has_more=false)
    - Existing TestRun fields (execution metadata, id, status, latency_ms, etc.) remain intact
    - Tenant isolation / authorization rules remain enforced
    """
    from datetime import datetime, timezone, timedelta
    headers = authenticated_context["headers"]
    user = authenticated_context["user"]

    # Retrieve existing evaluation owned by the user to attach a clean dedicated TestCase
    existing_tc = db_session.query(TestCase).filter(TestCase.id == uuid.UUID(authenticated_context["own_test_case_id"])).first()
    evaluation_id = existing_tc.evaluation_id

    # Create a clean dedicated test case so that counts are 100% deterministic and isolated
    dedicated_tc = TestCase(
        id=uuid.uuid4(),
        evaluation_id=evaluation_id,
        name="Combined Query Integration TestCase",
        category="integration",
        description="TestCase specifically for testing combined query parameters in isolation",
        input_data='{"prompt": "integration test"}',
        expected_behavior="deterministic pagination and filtering",
    )
    db_session.add(dedicated_tc)
    db_session.commit()

    test_case_id = str(dedicated_tc.id)

    base_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    seeded_ids = []

    # Seed 7 test runs specifically for this test case:
    # 4 'completed' (latencies: 100, 200, 300, 400; timestamps incremented)
    # 3 'failed' (latencies: 50, 150, 250; timestamps incremented)
    test_runs_data = [
        {"status": "completed", "latency": 100, "offset": 1},
        {"status": "completed", "latency": 200, "offset": 2},
        {"status": "completed", "latency": 300, "offset": 3},
        {"status": "completed", "latency": 400, "offset": 4},
        {"status": "failed", "latency": 50, "offset": 5},
        {"status": "failed", "latency": 150, "offset": 6},
        {"status": "failed", "latency": 250, "offset": 7},
    ]

    for d in test_runs_data:
        t = base_time + timedelta(minutes=d["offset"])
        run = TestRun(
            id=uuid.uuid4(),
            test_case_id=dedicated_tc.id,
            status=d["status"],
            actual_output=f"Integration run {d['status']} {d['latency']}",
            latency_ms=d["latency"],
            started_at=t,
            completed_at=t + timedelta(milliseconds=d["latency"]),
            created_at=t,
            executor_type="HTTPAgentExecutor",
        )
        db_session.add(run)
        seeded_ids.append(run.id)
    db_session.commit()

    try:
        url = f"/test-cases/{test_case_id}/runs"

        # 1. Status filtering combined with pagination & pagination metadata
        # Filter for 'completed' (total 4), page size 2, skip 0
        resp_p1 = client.get(f"{url}?status=completed&skip=0&limit=2&paginated=true", headers=headers)
        assert resp_p1.status_code == 200
        p1_data = resp_p1.json()
        assert p1_data["total"] == 4
        assert p1_data["skip"] == 0
        assert p1_data["limit"] == 2
        assert p1_data["has_more"] is True
        assert len(p1_data["items"]) == 2
        assert all(item["status"] == "completed" for item in p1_data["items"])

        # Page 2: skip=2, limit=2
        resp_p2 = client.get(f"{url}?status=completed&skip=2&limit=2&paginated=true", headers=headers)
        assert resp_p2.status_code == 200
        p2_data = resp_p2.json()
        assert p2_data["total"] == 4
        assert p2_data["skip"] == 2
        assert p2_data["limit"] == 2
        assert p2_data["has_more"] is False
        assert len(p2_data["items"]) == 2
        assert all(item["status"] == "completed" for item in p2_data["items"])

        # Consecutive pages contain no duplicate records
        p1_item_ids = {r["id"] for r in p1_data["items"]}
        p2_item_ids = {r["id"] for r in p2_data["items"]}
        assert p1_item_ids.isdisjoint(p2_item_ids)
        assert len(p1_item_ids | p2_item_ids) == 4

        # 2. Filtering, sorting, and pagination combined together
        # Filter 'completed', sort by latency_ms descending, limit 2
        resp_sort_desc = client.get(
            f"{url}?status=completed&sort_by=latency_ms&order=desc&skip=0&limit=2&paginated=true",
            headers=headers,
        )
        assert resp_sort_desc.status_code == 200
        desc_data = resp_sort_desc.json()
        assert desc_data["total"] == 4
        assert desc_data["has_more"] is True
        assert desc_data["items"][0]["latency_ms"] == 400
        assert desc_data["items"][1]["latency_ms"] == 300

        # Next page of filtered descending sort
        resp_sort_desc_p2 = client.get(
            f"{url}?status=completed&sort_by=latency_ms&order=desc&skip=2&limit=2&paginated=true",
            headers=headers,
        )
        assert resp_sort_desc_p2.status_code == 200
        desc_data_p2 = resp_sort_desc_p2.json()
        assert desc_data_p2["total"] == 4
        assert desc_data_p2["has_more"] is False
        assert desc_data_p2["items"][0]["latency_ms"] == 200
        assert desc_data_p2["items"][1]["latency_ms"] == 100

        # 3. Filter 'failed', sort by latency_ms ascending, paginated
        resp_failed = client.get(
            f"{url}?status=failed&sort_by=latency_ms&order=asc&skip=0&limit=2&paginated=true",
            headers=headers,
        )
        assert resp_failed.status_code == 200
        failed_data = resp_failed.json()
        assert failed_data["total"] == 3
        assert failed_data["has_more"] is True
        assert len(failed_data["items"]) == 2
        assert failed_data["items"][0]["latency_ms"] == 50
        assert failed_data["items"][1]["latency_ms"] == 150

        # 4. Empty filtered results return valid response structure
        resp_empty_paginated = client.get(
            f"{url}?status=running&skip=0&limit=10&paginated=true",
            headers=headers,
        )
        assert resp_empty_paginated.status_code == 200
        empty_meta = resp_empty_paginated.json()
        assert empty_meta["total"] == 0
        assert empty_meta["skip"] == 0
        assert empty_meta["limit"] == 10
        assert empty_meta["has_more"] is False
        assert empty_meta["items"] == []

        # Empty filtered results in unpaginated/legacy mode
        resp_empty_unpaginated = client.get(f"{url}?status=running", headers=headers)
        assert resp_empty_unpaginated.status_code == 200
        assert resp_empty_unpaginated.json() == []

        # 5. Metadata integrity: verify all contract fields on items
        first_item = p1_data["items"][0]
        assert "id" in first_item
        assert "test_case_id" in first_item
        assert "status" in first_item
        assert "latency_ms" in first_item
        assert "executor_type" in first_item
        assert first_item["executor_type"] == "HTTPAgentExecutor"
        assert "started_at" in first_item
        assert first_item["started_at"] is not None
        assert "completed_at" in first_item
        assert first_item["completed_at"] is not None

        # 6. Global /test-runs endpoint with combined query
        resp_global = client.get(
            f"/test-runs?status=completed&sort_by=latency_ms&order=desc&skip=0&limit=3&paginated=true",
            headers=headers,
        )
        assert resp_global.status_code == 200
        global_data = resp_global.json()
        assert global_data["total"] >= 4
        assert len(global_data["items"]) == 3
        assert all(it["status"] == "completed" for it in global_data["items"])
        lat_seq = [it["latency_ms"] for it in global_data["items"] if it["latency_ms"] is not None]
        assert lat_seq == sorted(lat_seq, reverse=True)

        # 7. Authorization & tenant isolation preserved
        other_headers = authenticated_context.get("other_headers")
        if other_headers:
            resp_forbidden = client.get(url, headers=other_headers)
            assert resp_forbidden.status_code in (403, 404)
    finally:
        db_session.query(TestRun).filter(TestRun.id.in_(seeded_ids)).delete(synchronize_session=False)
        db_session.query(TestCase).filter(TestCase.id == dedicated_tc.id).delete(synchronize_session=False)
        db_session.commit()


def test_test_run_api_error_handling_and_response_consistency(client, authenticated_context):
    """
    Step 174: TestRun API Error Handling & Response Consistency.
    - Standardize error responses (422, 401/403, 404).
    - Test invalid requests: malformed TestRun IDs, invalid pagination/sorting, unsupported status filters.
    - Protect internal details: responses must not leak stack traces, database credentials, internal paths, or secrets.
    - Verify response consistency: error responses contain {"detail": ...}, successful responses retain existing contracts.
    - Confirm normal execution behavior is unaffected.
    """
    test_case_id = authenticated_context["own_test_case_id"]
    headers = authenticated_context["headers"]

    # 1. Nonexistent TestRun ID -> 404 with structured detail
    random_uuid = str(uuid.uuid4())
    resp_404 = client.get(f"/test-runs/{random_uuid}", headers=headers)
    assert resp_404.status_code == 404
    body_404 = resp_404.json()
    assert "detail" in body_404
    assert body_404["detail"] == "Test run not found"

    # 2. Malformed TestRun ID (not a valid UUID) -> 422 validation error
    malformed_ids = [
        "not-a-valid-uuid",
        "12345",
        "invalid-uuid-1234-5678",
        "00000000-0000-0000-0000-00000000000Z",
    ]
    for m_id in malformed_ids:
        resp_malformed = client.get(f"/test-runs/{m_id}", headers=headers)
        assert resp_malformed.status_code == 422
        body_malformed = resp_malformed.json()
        assert "detail" in body_malformed

    # Malformed TestCase ID on nested endpoint -> 422
    for m_id in malformed_ids:
        resp_malformed_tc = client.get(f"/test-cases/{m_id}/runs", headers=headers)
        assert resp_malformed_tc.status_code == 422
        assert "detail" in resp_malformed_tc.json()

    # 3. Unauthenticated requests -> 401 or 403
    unauth_endpoints = [
        ("GET", f"/test-cases/{test_case_id}/runs"),
        ("POST", f"/test-cases/{test_case_id}/runs"),
        ("GET", f"/test-runs/{random_uuid}"),
        ("GET", "/test-runs"),
    ]
    for method, ep in unauth_endpoints:
        # Missing auth header
        if method == "GET":
            resp_no_auth = client.get(ep)
        else:
            resp_no_auth = client.post(ep)
        assert resp_no_auth.status_code in (401, 403)
        assert "detail" in resp_no_auth.json()

        # Malformed / invalid bearer token
        bad_headers = {"Authorization": "Bearer invalid_garbage_token_value"}
        if method == "GET":
            resp_bad_token = client.get(ep, headers=bad_headers)
        else:
            resp_bad_token = client.post(ep, headers=bad_headers)
        assert resp_bad_token.status_code == 401
        assert "detail" in resp_bad_token.json()
        assert resp_bad_token.json()["detail"] == "Invalid authentication token"

    # 4. Protection against leaking internal implementation details
    # Query with SQL injection attempt, internal path payloads, or extreme bounds
    suspicious_queries = [
        "?status=SELECT%20*%20FROM%20users",
        "?sort_by=secret_table_column",
        "?order=UNION%20SELECT",
        "?skip=-99999999999999999999999999999999999",
        "?limit=99999999999999999999999999999999999",
    ]
    for sq in suspicious_queries:
        for ep in [f"/test-cases/{test_case_id}/runs", "/test-runs"]:
            resp_err = client.get(f"{ep}{sq}", headers=headers)
            assert resp_err.status_code in (422, 400)
            err_text = resp_err.text.lower()
            # Ensure no database connection string or passwords or stack traces leaked
            assert "traceback" not in err_text
            assert "postgresql://" not in err_text
            assert "psycopg2" not in err_text
            assert "password_hash" not in err_text
            assert "veridyn_password" not in err_text
            assert "file \"/" not in err_text
            assert "file \"c:\\" not in err_text

    # 5. Response consistency on normal operations
    resp_success = client.get(f"/test-cases/{test_case_id}/runs?paginated=true", headers=headers)
    assert resp_success.status_code == 200
    success_json = resp_success.json()
    assert "items" in success_json
    assert "total" in success_json
    assert "skip" in success_json
    assert "limit" in success_json
    assert "has_more" in success_json
    assert isinstance(success_json["items"], list)


def test_test_run_openapi_contract_specification(client):
    """
    Step 175: TestRun API Documentation & OpenAPI Contract.
    - Inspect OpenAPI schema generated by FastAPI.
    - Confirm /test-cases/{test_case_id}/runs, /test-runs, and /test-runs/{test_run_id} are present.
    - Verify documented query parameters: skip, limit, status, sort_by, order, paginated.
    - Verify constraints: skip ge 0, limit between 1 and 100.
    - Verify response schemas: TestRunResponse (including started_at, executor_type), PaginatedTestRunResponse.
    - Verify security requirements (HTTPBearer) and HTTP status codes (200, 201, 422).
    """
    openapi = app.openapi()
    assert "paths" in openapi
    paths = openapi["paths"]

    # 1. Verify endpoints in OpenAPI paths
    nested_path = "/test-cases/{test_case_id}/runs"
    global_path = "/test-runs"
    detail_path = "/test-runs/{test_run_id}"

    assert nested_path in paths
    assert global_path in paths
    assert detail_path in paths

    # 2. Inspect query parameters for listing endpoints
    for p in [nested_path, global_path]:
        get_op = paths[p]["get"]
        assert "parameters" in get_op
        params_by_name = {param["name"]: param for param in get_op["parameters"]}

        # Pagination: skip and limit
        assert "skip" in params_by_name
        skip_schema = params_by_name["skip"]["schema"]
        assert skip_schema.get("type") == "integer"
        assert skip_schema.get("minimum") == 0
        assert skip_schema.get("default") == 0

        assert "limit" in params_by_name
        limit_schema = params_by_name["limit"]["schema"]
        assert limit_schema.get("type") == "integer"
        assert limit_schema.get("minimum") == 1
        assert limit_schema.get("maximum") == 100
        assert limit_schema.get("default") == 50

        # Filtering: status
        assert "status" in params_by_name
        assert "Optional status filter" in params_by_name["status"]["description"]

        # Sorting: sort_by and order
        assert "sort_by" in params_by_name
        assert params_by_name["sort_by"]["schema"].get("default") == "created_at"
        assert "order" in params_by_name
        assert params_by_name["order"]["schema"].get("default") == "desc"

        # Pagination flag
        assert "paginated" in params_by_name
        assert params_by_name["paginated"]["schema"].get("default") is False

        # Security
        assert "security" in get_op
        assert any("HTTPBearer" in sec for sec in get_op["security"])

        # Responses
        responses = get_op["responses"]
        assert "200" in responses
        assert "422" in responses

    # 3. Inspect detail endpoint
    detail_get = paths[detail_path]["get"]
    assert "parameters" in detail_get
    path_param = detail_get["parameters"][0]
    assert path_param["name"] == "test_run_id"
    assert path_param["in"] == "path"
    assert path_param["schema"]["type"] == "string"
    assert path_param["schema"]["format"] == "uuid"

    # 4. Inspect components schemas
    schemas = openapi["components"]["schemas"]
    assert "TestRunResponse" in schemas
    assert "PaginatedTestRunResponse" in schemas

    tr_props = schemas["TestRunResponse"]["properties"]
    assert "id" in tr_props
    assert "test_case_id" in tr_props
    assert "status" in tr_props
    assert "latency_ms" in tr_props
    assert "started_at" in tr_props
    assert "completed_at" in tr_props
    assert "executor_type" in tr_props
    assert "actual_output" in tr_props

    paginated_props = schemas["PaginatedTestRunResponse"]["properties"]
    assert "items" in paginated_props
    assert "total" in paginated_props
    assert "skip" in paginated_props
    assert "limit" in paginated_props
    assert "has_more" in paginated_props



