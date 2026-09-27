from app.models.evaluation import Evaluation
from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.models.agent_version import AgentVersion


def test_evaluation_primary_key():
    column = Evaluation.__table__.c.id

    assert column.primary_key is True
    assert column.nullable is False


def test_test_case_primary_key():
    column = TestCase.__table__.c.id

    assert column.primary_key is True
    assert column.nullable is False


def test_test_run_primary_key():
    column = TestRun.__table__.c.id

    assert column.primary_key is True
    assert column.nullable is False


def test_agent_version_primary_key():
    column = AgentVersion.__table__.c.id

    assert column.primary_key is True
    assert column.nullable is False
