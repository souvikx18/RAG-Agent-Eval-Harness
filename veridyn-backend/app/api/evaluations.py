from datetime import datetime, timezone

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
        .join(Agent)
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
        started_at=None,
        completed_at=None,
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
    agent_version_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent_version = (
        db.query(AgentVersion)
        .join(Agent)
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