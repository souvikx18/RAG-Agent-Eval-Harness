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
from app.schemas.test_run import TestRunResponse
from app.services.agent_execution_service import execute_test_run

router = APIRouter(
    prefix="/test-cases/{test_case_id}/runs",
    tags=["Test Runs"],
)


def get_owned_test_case(
    test_case_id: str,
    current_user: User,
    db: Session,
):
    test_case = (
        db.query(TestCase)
        .join(Evaluation)
        .join(AgentVersion)
        .join(Agent)
        .filter(
            TestCase.id == test_case_id,
            Agent.owner_id == current_user.id,
        )
        .first()
    )

    if not test_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test case not found",
        )

    return test_case


@router.post(
    "",
    response_model=TestRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_test_run(
    test_case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    test_case = get_owned_test_case(
        test_case_id,
        current_user,
        db,
    )

    test_run = TestRun(
        test_case_id=test_case.id,
        status="pending",
    )

    db.add(test_run)
    db.commit()
    db.refresh(test_run)

    return execute_test_run(test_run, db)


@router.get(
    "",
    response_model=list[TestRunResponse],
)
def list_test_runs(
    test_case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    test_case = get_owned_test_case(
        test_case_id,
        current_user,
        db,
    )

    return (
        db.query(TestRun)
        .filter(TestRun.test_case_id == test_case.id)
        .order_by(TestRun.created_at.desc())
        .all()
    )