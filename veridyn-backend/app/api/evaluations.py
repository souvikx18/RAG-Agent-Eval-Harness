import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.agent import Agent
from app.models.agent_version import AgentVersion
from app.models.evaluation import Evaluation
from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.models.user import User
from app.schemas.evaluation import (
    EvaluationCreateRequest,
    EvaluationResponse,
)
from app.services.evaluation_service import (
    start_evaluation,
    complete_evaluation,
)


router = APIRouter(
    prefix="/evaluations",
    tags=["Evaluations"],
)


def build_evaluation_response(
    evaluation: Evaluation,
    db: Session,
) -> dict:

    test_runs = (
        db.query(TestRun)
        .join(
            TestCase,
            TestRun.test_case_id == TestCase.id,
        )
        .filter(
            TestCase.evaluation_id == evaluation.id
        )
        .all()
    )

    total_runs = len(test_runs)

    passed_runs = sum(
        1
        for test_run in test_runs
        if test_run.status == "completed"
        and test_run.result == "passed"
    )

    failed_runs = sum(
        1
        for test_run in test_runs
        if test_run.status == "failed"
        or test_run.result == "failed"
    )

    latency_values = [
        test_run.latency_ms
        for test_run in test_runs
        if test_run.latency_ms is not None
    ]

    average_latency_ms = (
        sum(latency_values) / len(latency_values)
        if latency_values
        else 0.0
    )

    return {
        "id": evaluation.id,
        "agent_version_id": evaluation.agent_version_id,
        "status": evaluation.status,
        "trigger_type": evaluation.trigger_type,
        "summary": evaluation.summary,
        "overall_score": evaluation.overall_score,
        "total_runs": total_runs,
        "passed_runs": passed_runs,
        "failed_runs": failed_runs,
        "average_latency_ms": round(
            average_latency_ms,
            2,
        ),
    }


@router.post(
    "",
    response_model=EvaluationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_evaluation(
    data: EvaluationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent_version = (
        db.query(AgentVersion)
        .join(
            Agent,
            AgentVersion.agent_id == Agent.id,
        )
        .filter(
            AgentVersion.id == data.agent_version_id,
            Agent.owner_id == current_user.id,
        )
        .first()
    )

    if not agent_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent version not found",
        )

    evaluation = Evaluation(
        agent_version_id=agent_version.id,
        status="pending",
        trigger_type=data.trigger_type,
    )

    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)

    return build_evaluation_response(
        evaluation,
        db,
    )


@router.get(
    "/{agent_version_id}",
    response_model=list[EvaluationResponse],
)
def list_evaluations(
    agent_version_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent_version = (
        db.query(AgentVersion)
        .join(
            Agent,
            AgentVersion.agent_id == Agent.id,
        )
        .filter(
            AgentVersion.id == agent_version_id,
            Agent.owner_id == current_user.id,
        )
        .first()
    )

    if not agent_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent version not found",
        )

    evaluations = (
        db.query(Evaluation)
        .filter(
            Evaluation.agent_version_id == agent_version.id
        )
        .order_by(Evaluation.created_at.desc())
        .all()
    )

    return [
        build_evaluation_response(
            ev,
            db,
        )
        for ev in evaluations
    ]


@router.post(
    "/{evaluation_id}/start",
    response_model=EvaluationResponse,
)
def start_evaluation_endpoint(
    evaluation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    evaluation = (
        db.query(Evaluation)
        .join(
            AgentVersion,
            Evaluation.agent_version_id == AgentVersion.id,
        )
        .join(
            Agent,
            AgentVersion.agent_id == Agent.id,
        )
        .filter(
            Evaluation.id == evaluation_id,
            Agent.owner_id == current_user.id,
        )
        .first()
    )

    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation not found",
        )

    if evaluation.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Evaluation has already started",
        )

    evaluation = start_evaluation(
        evaluation,
        db,
    )

    return build_evaluation_response(
        evaluation,
        db,
    )


@router.post(
    "/{evaluation_id}/complete",
    response_model=EvaluationResponse,
)
def complete_evaluation_endpoint(
    evaluation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    evaluation = (
        db.query(Evaluation)
        .join(
            AgentVersion,
            Evaluation.agent_version_id == AgentVersion.id,
        )
        .join(
            Agent,
            AgentVersion.agent_id == Agent.id,
        )
        .filter(
            Evaluation.id == evaluation_id,
            Agent.owner_id == current_user.id,
        )
        .first()
    )

    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation not found",
        )

    if evaluation.status != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Evaluation is not running",
        )

    evaluation = complete_evaluation(
        evaluation,
        db,
    )

    return build_evaluation_response(
        evaluation,
        db,
    )