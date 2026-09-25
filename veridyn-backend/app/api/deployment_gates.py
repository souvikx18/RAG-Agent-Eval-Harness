import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.agent import Agent
from app.models.agent_version import AgentVersion
from app.models.deployment_gate import DeploymentGate
from app.models.evaluation import Evaluation
from app.models.user import User
from app.schemas.deployment_gate import DeploymentGateResponse


router = APIRouter(
    prefix="/evaluations/{evaluation_id}/deployment-gate",
    tags=["Deployment Gate"],
)


def get_owned_evaluation(
    evaluation_id: uuid.UUID,
    current_user: User,
    db: Session,
) -> Evaluation:
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

    return evaluation


@router.post(
    "",
    response_model=DeploymentGateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_deployment_gate(
    evaluation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    evaluation = get_owned_evaluation(
        evaluation_id,
        current_user,
        db,
    )

    gate = DeploymentGate(
        evaluation_id=evaluation.id,
        decision="REVIEW",
        overall_score=None,
        reason="Deployment gate created. Automated scoring will determine the final decision.",
    )

    db.add(gate)
    db.commit()
    db.refresh(gate)

    return gate


@router.get(
    "",
    response_model=list[DeploymentGateResponse],
)
def list_deployment_gates(
    evaluation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    evaluation = get_owned_evaluation(
        evaluation_id,
        current_user,
        db,
    )

    return (
        db.query(DeploymentGate)
        .filter(
            DeploymentGate.evaluation_id == evaluation.id
        )
        .order_by(DeploymentGate.created_at.desc())
        .all()
    )