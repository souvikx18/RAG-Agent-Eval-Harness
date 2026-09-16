from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.agent import Agent
from app.models.agent_version import AgentVersion
from app.models.user import User
from app.schemas.agent_version import (
    AgentVersionCreateRequest,
    AgentVersionResponse,
)


router = APIRouter(
    prefix="/agents/{agent_id}/versions",
    tags=["Agent Versions"],
)


@router.post(
    "",
    response_model=AgentVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_agent_version(
    agent_id: str,
    data: AgentVersionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = (
        db.query(Agent)
        .filter(
            Agent.id == agent_id,
            Agent.owner_id == current_user.id,
        )
        .first()
    )

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    version = AgentVersion(
        agent_id=agent.id,
        version=data.version,
        description=data.description,
        endpoint=data.endpoint,
        config_hash=data.config_hash,
    )

    db.add(version)
    db.commit()
    db.refresh(version)

    return version


@router.get(
    "",
    response_model=list[AgentVersionResponse],
)
def list_agent_versions(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = (
        db.query(Agent)
        .filter(
            Agent.id == agent_id,
            Agent.owner_id == current_user.id,
        )
        .first()
    )

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    return (
        db.query(AgentVersion)
        .filter(AgentVersion.agent_id == agent.id)
        .all()
    )