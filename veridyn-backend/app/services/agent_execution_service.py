import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.agent_version import AgentVersion
from app.models.evaluation import Evaluation
from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.services.executors.agent_executor import (
    AgentExecutionRequest,
)
from app.services.executors.factory import get_agent_executor


def execute_test_run(
    test_run: TestRun,
    db: Session,
) -> TestRun:

    start_time = time.perf_counter()

    try:
        test_case = (
            db.query(TestCase)
            .filter(
                TestCase.id == test_run.test_case_id
            )
            .first()
        )

        if not test_case:
            raise ValueError("Test case not found")

        evaluation = (
            db.query(Evaluation)
            .filter(
                Evaluation.id == test_case.evaluation_id
            )
            .first()
        )

        if not evaluation:
            raise ValueError("Evaluation not found")

        agent_version = (
            db.query(AgentVersion)
            .filter(
                AgentVersion.id
                == evaluation.agent_version_id
            )
            .first()
        )

        if not agent_version:
            raise ValueError("Agent version not found")

        test_run.status = "running"
        db.commit()

        request = AgentExecutionRequest(
            input_data=test_case.input_data,
            endpoint=agent_version.endpoint,
            config_hash=agent_version.config_hash,
        )

        executor = get_agent_executor(
            endpoint=agent_version.endpoint,
        )

        response = executor.execute(request)

        test_run.latency_ms = response.latency_ms
        test_run.completed_at = datetime.now(timezone.utc)

        if response.error:
            test_run.status = "failed"
            test_run.error_message = response.error
            test_run.actual_output = None
            test_run.result = "failed"
        else:
            test_run.status = "completed"
            test_run.actual_output = response.output
            test_run.result = "passed"
            test_run.error_message = None

    except Exception as exc:
        test_run.status = "failed"
        test_run.error_message = str(exc)
        test_run.completed_at = datetime.now(timezone.utc)
        test_run.latency_ms = int(
            (time.perf_counter() - start_time) * 1000
        )

    db.commit()
    db.refresh(test_run)

    return test_run