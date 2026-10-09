import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.agent import Agent
from app.models.agent_version import AgentVersion
from app.models.evaluation import Evaluation
from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.models.user import User
from app.schemas.test_run import PaginatedTestRunResponse, TestRunResponse
from app.services.agent_execution_service import execute_test_run
from app.services.result_service import create_evaluation_result

router = APIRouter(
    prefix="/test-cases/{test_case_id}/runs",
    tags=["Test Runs"],
)


def get_owned_test_case(
    test_case_id: uuid.UUID,
    current_user: User,
    db: Session,
) -> TestCase:
    test_case = (
        db.query(TestCase)
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
    test_case_id: uuid.UUID,
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

    test_run = execute_test_run(test_run, db)
    create_evaluation_result(test_run, db)
    return test_run


ALLOWED_TEST_RUN_STATUSES = {"pending", "running", "completed", "failed"}


@router.get(
    "",
    response_model=PaginatedTestRunResponse | list[TestRunResponse],
)
def list_test_runs(
    test_case_id: uuid.UUID,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    status: str | None = Query(None, description="Optional status filter"),
    paginated: bool = Query(False, description="Return wrapped pagination envelope"),
    response: Response = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    test_case = get_owned_test_case(
        test_case_id,
        current_user,
        db,
    )

    query = db.query(TestRun).filter(TestRun.test_case_id == test_case.id)

    if status is not None:
        if status not in ALLOWED_TEST_RUN_STATUSES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status: {status}. Allowed statuses: {sorted(ALLOWED_TEST_RUN_STATUSES)}",
            )
        query = query.filter(TestRun.status == status)

    total = query.count()
    items = (
        query.order_by(TestRun.created_at.desc(), TestRun.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    has_more = (skip + len(items)) < total

    if response is not None:
        response.headers["X-Total-Count"] = str(total)
        response.headers["X-Has-More"] = str(has_more).lower()

    if paginated:
        return PaginatedTestRunResponse(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
            has_more=has_more,
        )

    return items


detail_router = APIRouter(
    prefix="/test-runs",
    tags=["Test Runs"],
)


@detail_router.get(
    "",
    response_model=PaginatedTestRunResponse | list[TestRunResponse],
)
def list_user_test_runs(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    status: str | None = Query(None, description="Optional status filter"),
    paginated: bool = Query(False, description="Return wrapped pagination envelope"),
    response: Response = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        db.query(TestRun)
        .join(TestCase, TestRun.test_case_id == TestCase.id)
        .join(Evaluation, TestCase.evaluation_id == Evaluation.id)
        .join(AgentVersion, Evaluation.agent_version_id == AgentVersion.id)
        .join(Agent, AgentVersion.agent_id == Agent.id)
        .filter(Agent.owner_id == current_user.id)
    )

    if status is not None:
        if status not in ALLOWED_TEST_RUN_STATUSES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status: {status}. Allowed statuses: {sorted(ALLOWED_TEST_RUN_STATUSES)}",
            )
        query = query.filter(TestRun.status == status)

    total = query.count()
    items = (
        query.order_by(TestRun.created_at.desc(), TestRun.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    has_more = (skip + len(items)) < total

    if response is not None:
        response.headers["X-Total-Count"] = str(total)
        response.headers["X-Has-More"] = str(has_more).lower()

    if paginated:
        return PaginatedTestRunResponse(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
            has_more=has_more,
        )

    return items


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


@detail_router.get(
    "/{test_run_id}",
    response_model=TestRunResponse,
)
def get_test_run(
    test_run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_owned_test_run(
        test_run_id,
        current_user,
        db,
    )