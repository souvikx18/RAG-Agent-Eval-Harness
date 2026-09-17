import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.agent import Agent
from app.models.agent_version import AgentVersion
from app.models.evaluation import Evaluation
from app.models.user import User
from app.schemas.evaluation import (
    EvaluationCreateRequest,
    EvaluationResponse,
)
from app.services.evaluation_service import start_evaluation


router = APIRouter(
    prefix="/evaluations",
    tags=["Evaluations"],
)


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

    return evaluation


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

    return (
        db.query(Evaluation)
        .filter(
            Evaluation.agent_version_id == agent_version.id
        )
        .order_by(Evaluation.created_at.desc())
        .all()
    )


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

    return start_evaluation(
        evaluation,
        db,
    )