import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.agent import Agent
from app.models.agent_version import AgentVersion
from app.models.evaluation import Evaluation
from app.models.execution_trace import ExecutionTrace
from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.models.user import User
from app.schemas.execution_trace import (
    ExecutionTraceCreateRequest,
    ExecutionTraceResponse,
)


router = APIRouter(
    prefix="/test-runs/{test_run_id}/traces",
    tags=["Execution Traces"],
)


def get_owned_test_run(
    test_run_id: uuid.UUID,
    current_user: User,
    db: Session,
) -> TestRun:
    test_run = (
        db.query(TestRun)
        .join(
            TestCase,
            TestRun.test_case_id == TestCase.id,
        )
        .join(
            Evaluation,
            TestCase.evaluation_id == Evaluation.id,
        )
        .join(
            AgentVersion,
            Evaluation.agent_version_id == AgentVersion.id,
        )
        .join(
            Agent,
            AgentVersion.agent_id == Agent.id,
        )
        .filter(
            TestRun.id == test_run_id,
            Agent.owner_id == current_user.id,
        )
        .first()
    )

    if not test_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test run not found",
        )

    return test_run


@router.post(
    "",
    response_model=ExecutionTraceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_execution_trace(
    test_run_id: uuid.UUID,
    data: ExecutionTraceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    test_run = get_owned_test_run(
        test_run_id,
        current_user,
        db,
    )

    trace = ExecutionTrace(
        test_run_id=test_run.id,
        trace_type=data.trace_type,
        name=data.name,
        input_data=data.input_data,
        output_data=data.output_data,
        error_message=data.error_message,
        latency_ms=data.latency_ms,
    )

    db.add(trace)
    db.commit()
    db.refresh(trace)

    return trace


@router.get(
    "",
    response_model=list[ExecutionTraceResponse],
)
def list_execution_traces(
    test_run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    test_run = get_owned_test_run(
        test_run_id,
        current_user,
        db,
    )

    return (
        db.query(ExecutionTrace)
        .filter(
            ExecutionTrace.test_run_id == test_run.id
        )
        .order_by(ExecutionTrace.created_at.asc())
        .all()
    )