from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.agent import Agent
from app.models.user import User
from app.schemas.agent import AgentCreateRequest, AgentResponse


router = APIRouter(
    prefix="/agents",
    tags=["Agents"],
)


@router.post(
    "",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_agent(
    data: AgentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = Agent(
        owner_id=current_user.id,
        name=data.name,
        description=data.description,
        framework=data.framework,
    )

    db.add(agent)
    db.commit()
    db.refresh(agent)

    return agent


@router.get(
    "",
    response_model=list[AgentResponse],
)
def list_agents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Agent)
        .filter(Agent.owner_id == current_user.id)
        .all()
    )


@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
)
def get_agent(
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

    return agent