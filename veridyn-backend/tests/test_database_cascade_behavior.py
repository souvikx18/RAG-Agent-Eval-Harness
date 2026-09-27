import uuid

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.user import User
from app.models.agent import Agent
from app.models.agent_version import AgentVersion
from app.models.evaluation import Evaluation
from app.models.test_case import TestCase
from app.models.test_run import TestRun


def test_deleting_evaluation_cascades_to_test_cases_and_runs():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    db = TestingSessionLocal()

    try:
        user = User(
            email=f"cascade-{uuid.uuid4()}@example.com",
            hashed_password="test-password",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        agent = Agent(
            owner_id=user.id,
            name="Cascade Test Agent",
            description="Agent used for cascade testing",
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)

        agent_version = AgentVersion(
            agent_id=agent.id,
            version="1.0.0",
        )
        db.add(agent_version)
        db.commit()
        db.refresh(agent_version)

        evaluation = Evaluation(
            agent_version_id=agent_version.id,
            status="completed",
            trigger_type="manual",
        )
        db.add(evaluation)
        db.commit()
        db.refresh(evaluation)

        test_case = TestCase(
            evaluation_id=evaluation.id,
            name="Cascade Test",
            category="functional",
            input_data="Hello",
            expected_behavior="Successful response",
            is_adversarial=False,
        )
        db.add(test_case)
        db.commit()
        db.refresh(test_case)

        test_run = TestRun(
            test_case_id=test_case.id,
            status="completed",
            result="passed",
            latency_ms=100,
        )
        db.add(test_run)
        db.commit()
        db.refresh(test_run)

        evaluation_id = evaluation.id
        test_case_id = test_case.id
        test_run_id = test_run.id

        db.execute(
            Evaluation.__table__.delete().where(
                Evaluation.id == evaluation_id
            )
        )
        db.commit()

        assert db.query(Evaluation).filter(
            Evaluation.id == evaluation_id
        ).first() is None

        assert db.query(TestCase).filter(
            TestCase.id == test_case_id
        ).first() is None

        assert db.query(TestRun).filter(
            TestRun.id == test_run_id
        ).first() is None

    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
