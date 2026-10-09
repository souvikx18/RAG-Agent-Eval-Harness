import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.agent import Agent
from app.models.agent_version import AgentVersion
from app.models.evaluation import Evaluation
from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.models.user import User
from app.services.agent_execution_service import execute_test_run


@pytest.fixture
def execution_hierarchy(db):
    user = User(
        id=uuid.uuid4(),
        email=f"user_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="hashed_pw",
    )
    db.add(user)
    db.commit()

    agent = Agent(
        id=uuid.uuid4(),
        name="Metadata Test Agent",
        description="Agent for testing run metadata",
        owner_id=user.id,
    )
    db.add(agent)
    db.commit()

    placeholder_version = AgentVersion(
        id=uuid.uuid4(),
        agent_id=agent.id,
        version="1.0",
        endpoint=None,
        config_hash="placeholder_hash",
    )
    http_version = AgentVersion(
        id=uuid.uuid4(),
        agent_id=agent.id,
        version="2.0",
        endpoint="http://127.0.0.1:9000/agent",
        config_hash="http_hash",
    )
    db.add_all([placeholder_version, http_version])
    db.commit()

    eval_placeholder = Evaluation(
        id=uuid.uuid4(),
        agent_version_id=placeholder_version.id,
        status="pending",
    )
    eval_http = Evaluation(
        id=uuid.uuid4(),
        agent_version_id=http_version.id,
        status="pending",
    )
    db.add_all([eval_placeholder, eval_http])
    db.commit()

    tc_placeholder = TestCase(
        id=uuid.uuid4(),
        evaluation_id=eval_placeholder.id,
        name="Placeholder TC",
        category="functional",
        input_data="Hello Placeholder",
        expected_behavior="Agent received input: Hello Placeholder",
        is_adversarial=False,
    )
    tc_http = TestCase(
        id=uuid.uuid4(),
        evaluation_id=eval_http.id,
        name="HTTP TC",
        category="functional",
        input_data="Hello HTTP",
        expected_behavior="Agent received input: Hello HTTP",
        is_adversarial=False,
    )
    db.add_all([tc_placeholder, tc_http])
    db.commit()

    return {
        "user": user,
        "agent": agent,
        "placeholder_version": placeholder_version,
        "http_version": http_version,
        "tc_placeholder": tc_placeholder,
        "tc_http": tc_http,
    }


def test_test_run_metadata_columns_exist():
    table = TestRun.__table__
    assert "started_at" in table.c
    assert "executor_type" in table.c
    assert table.c.started_at.nullable is True
    assert table.c.executor_type.nullable is True
    assert table.c.executor_type.type.length == 50


def test_execute_test_run_placeholder_metadata(db, execution_hierarchy):
    tc = execution_hierarchy["tc_placeholder"]

    test_run = TestRun(
        id=uuid.uuid4(),
        test_case_id=tc.id,
        status="pending",
    )
    db.add(test_run)
    db.commit()

    before_exec = datetime.now(timezone.utc)
    executed_run = execute_test_run(test_run, db)
    after_exec = datetime.now(timezone.utc)

    assert executed_run.status == "completed"
    assert executed_run.result == "passed"
    assert executed_run.executor_type == "PlaceholderAgentExecutor"
    assert executed_run.started_at is not None
    assert executed_run.completed_at is not None
    assert executed_run.latency_ms is not None
    assert executed_run.latency_ms >= 0
    started_at = (
        executed_run.started_at.replace(tzinfo=timezone.utc)
        if executed_run.started_at.tzinfo is None
        else executed_run.started_at
    )
    assert before_exec <= started_at <= after_exec
    assert executed_run.started_at <= executed_run.completed_at

    # Verify persistence
    reloaded = db.query(TestRun).filter(TestRun.id == test_run.id).first()
    assert reloaded is not None
    assert reloaded.executor_type == "PlaceholderAgentExecutor"
    assert reloaded.started_at == executed_run.started_at
    assert reloaded.completed_at == executed_run.completed_at
    assert reloaded.latency_ms == executed_run.latency_ms


def test_execute_test_run_http_metadata(db, execution_hierarchy):
    tc = execution_hierarchy["tc_http"]

    test_run = TestRun(
        id=uuid.uuid4(),
        test_case_id=tc.id,
        status="pending",
    )
    db.add(test_run)
    db.commit()

    with patch("httpx.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "output": "Agent received input: Hello HTTP"
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        executed_run = execute_test_run(test_run, db)

    assert executed_run.status == "completed"
    assert executed_run.result == "passed"
    assert executed_run.executor_type == "HTTPAgentExecutor"
    assert executed_run.started_at is not None
    assert executed_run.completed_at is not None
    assert executed_run.latency_ms is not None
    assert executed_run.started_at <= executed_run.completed_at

    # Verify persistence
    reloaded = db.query(TestRun).filter(TestRun.id == test_run.id).first()
    assert reloaded is not None
    assert reloaded.executor_type == "HTTPAgentExecutor"
    assert reloaded.started_at == executed_run.started_at
    assert reloaded.completed_at == executed_run.completed_at


def test_execute_test_run_failed_execution_retains_metadata(db, execution_hierarchy):
    tc = execution_hierarchy["tc_http"]

    test_run = TestRun(
        id=uuid.uuid4(),
        test_case_id=tc.id,
        status="pending",
    )
    db.add(test_run)
    db.commit()

    with patch("httpx.post", side_effect=RuntimeError("Connection refused by target host")):
        executed_run = execute_test_run(test_run, db)

    assert executed_run.status == "failed"
    assert executed_run.result is None or executed_run.result == "failed"
    assert "Connection refused" in (executed_run.error_message or "")
    # Crucial acceptance criteria: metadata must be retained on failure
    assert executed_run.executor_type == "HTTPAgentExecutor"
    assert executed_run.started_at is not None
    assert executed_run.completed_at is not None
    assert executed_run.latency_ms is not None

    # Verify persistence
    reloaded = db.query(TestRun).filter(TestRun.id == test_run.id).first()
    assert reloaded is not None
    assert reloaded.executor_type == "HTTPAgentExecutor"
    assert reloaded.started_at == executed_run.started_at
    assert reloaded.completed_at == executed_run.completed_at
    assert reloaded.status == "failed"


def test_execution_duration_consistency_successful_run(db, execution_hierarchy):
    tc = execution_hierarchy["tc_placeholder"]

    test_run = TestRun(
        id=uuid.uuid4(),
        test_case_id=tc.id,
        status="pending",
    )
    db.add(test_run)
    db.commit()

    executed_run = execute_test_run(test_run, db)

    assert executed_run.status == "completed"
    assert executed_run.started_at is not None
    assert executed_run.completed_at is not None
    assert executed_run.latency_ms is not None
    assert executed_run.latency_ms >= 0
    assert executed_run.completed_at >= executed_run.started_at


def test_execution_duration_consistency_failed_run(db, execution_hierarchy):
    tc = execution_hierarchy["tc_http"]

    test_run = TestRun(
        id=uuid.uuid4(),
        test_case_id=tc.id,
        status="pending",
    )
    db.add(test_run)
    db.commit()

    with patch("httpx.post", side_effect=Exception("Network failure")):
        executed_run = execute_test_run(test_run, db)

    assert executed_run.status == "failed"
    assert executed_run.started_at is not None
    assert executed_run.completed_at is not None
    assert executed_run.latency_ms is not None
    assert executed_run.latency_ms >= 0
    assert executed_run.completed_at >= executed_run.started_at


def test_execution_duration_consistency_failed_before_dispatch(db):
    """Failure prior to executor dispatch also guarantees consistent timing metadata."""
    test_run = TestRun(
        id=uuid.uuid4(),
        test_case_id=uuid.uuid4(),
        status="pending",
    )
    db.add(test_run)
    db.commit()

    executed_run = execute_test_run(test_run, db)

    assert executed_run.status == "failed"
    assert executed_run.started_at is not None
    assert executed_run.completed_at is not None
    assert executed_run.latency_ms is not None
    assert executed_run.latency_ms >= 0
    assert executed_run.completed_at >= executed_run.started_at


def test_test_run_metadata_persistence_regression(db, execution_hierarchy):
    """
    Step 165: Verify started_at and executor_type remain correct after saving to
    the database and retrieving again.
    """
    tc = execution_hierarchy["tc_http"]

    original_started_at = datetime.now(timezone.utc)
    original_executor_type = "HTTPAgentExecutor"

    test_run = TestRun(
        id=uuid.uuid4(),
        test_case_id=tc.id,
        status="completed",
        result="passed",
        actual_output="Output from HTTP execution",
        latency_ms=120,
        started_at=original_started_at,
        completed_at=datetime.now(timezone.utc),
        executor_type=original_executor_type,
    )
    db.add(test_run)
    db.commit()

    persisted_test_run = (
        db.query(TestRun)
        .filter(TestRun.id == test_run.id)
        .first()
    )

    assert persisted_test_run is not None
    assert persisted_test_run.started_at is not None

    persisted_started_at = (
        persisted_test_run.started_at.replace(tzinfo=timezone.utc)
        if persisted_test_run.started_at.tzinfo is None
        else persisted_test_run.started_at
    )
    assert persisted_started_at == original_started_at
    assert persisted_test_run.executor_type == "HTTPAgentExecutor"
    assert persisted_test_run.status == "completed"
    assert persisted_test_run.latency_ms == 120


def test_test_run_nullable_metadata_persistence(db, execution_hierarchy):
    """
    Step 165: Confirming that older or manually created records with None values
    for started_at and executor_type can still be persisted and loaded correctly.
    """
    tc = execution_hierarchy["tc_placeholder"]

    legacy_run = TestRun(
        id=uuid.uuid4(),
        test_case_id=tc.id,
        status="pending",
        started_at=None,
        executor_type=None,
        completed_at=None,
        latency_ms=None,
    )
    db.add(legacy_run)
    db.commit()

    reloaded_legacy = (
        db.query(TestRun)
        .filter(TestRun.id == legacy_run.id)
        .first()
    )

    assert reloaded_legacy is not None
    assert reloaded_legacy.started_at is None
    assert reloaded_legacy.executor_type is None
    assert reloaded_legacy.completed_at is None
    assert reloaded_legacy.latency_ms is None
    assert reloaded_legacy.status == "pending"


