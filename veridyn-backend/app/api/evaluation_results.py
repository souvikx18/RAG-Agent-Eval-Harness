import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.agent import Agent
from app.models.agent_version import AgentVersion
from app.models.evaluation import Evaluation
from app.models.evaluation_result import EvaluationResult
from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.models.user import User
from app.schemas.evaluation_result import (
    EvaluationResultCreateRequest,
    EvaluationResultResponse,
)


router = APIRouter(
    prefix="/test-runs/{test_run_id}/results",
    tags=["Evaluation Results"],
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
    response_model=EvaluationResultResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_evaluation_result(
    test_run_id: uuid.UUID,
    data: EvaluationResultCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    test_run = get_owned_test_run(
        test_run_id,
        current_user,
        db,
    )

    result = EvaluationResult(
        test_run_id=test_run.id,
        metric_name=data.metric_name,
        score=data.score,
        status=data.status,
        explanation=data.explanation,
    )

    db.add(result)
    db.commit()
    db.refresh(result)

    return result


@router.get(
    "",
    response_model=list[EvaluationResultResponse],
)
def list_evaluation_results(
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
        db.query(EvaluationResult)
        .filter(
            EvaluationResult.test_run_id == test_run.id
        )
        .order_by(EvaluationResult.created_at.asc())
        .all()
    )