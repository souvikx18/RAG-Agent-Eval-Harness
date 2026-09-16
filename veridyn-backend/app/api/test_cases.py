from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.agent import Agent
from app.models.agent_version import AgentVersion
from app.models.evaluation import Evaluation
from app.models.test_case import TestCase
from app.models.user import User
from app.schemas.test_case import (
    TestCaseCreateRequest,
    TestCaseResponse,
)


router = APIRouter(
    prefix="/evaluations/{evaluation_id}/test-cases",
    tags=["Test Cases"],
)


def get_owned_evaluation(
    evaluation_id: str,
    current_user: User,
    db: Session,
):
    evaluation = (
        db.query(Evaluation)
        .join(AgentVersion)
        .join(Agent)
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
    response_model=TestCaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_test_case(
    evaluation_id: str,
    data: TestCaseCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    evaluation = get_owned_evaluation(
        evaluation_id,
        current_user,
        db,
    )

    test_case = TestCase(
        evaluation_id=evaluation.id,
        name=data.name,
        category=data.category,
        description=data.description,
        input_data=data.input_data,
        expected_behavior=data.expected_behavior,
        is_adversarial=data.is_adversarial,
    )

    db.add(test_case)
    db.commit()
    db.refresh(test_case)

    return test_case


@router.get(
    "",
    response_model=list[TestCaseResponse],
)
def list_test_cases(
    evaluation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    evaluation = get_owned_evaluation(
        evaluation_id,
        current_user,
        db,
    )

    return (
        db.query(TestCase)
        .filter(TestCase.evaluation_id == evaluation.id)
        .order_by(TestCase.created_at.asc())
        .all()
    )