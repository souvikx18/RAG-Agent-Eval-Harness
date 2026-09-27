from app.models.test_case import TestCase
from app.models.test_run import TestRun


def test_test_case_evaluation_foreign_key():
    foreign_keys = TestCase.__table__.c.evaluation_id.foreign_keys

    assert len(foreign_keys) == 1

    foreign_key = next(iter(foreign_keys))

    assert foreign_key.target_fullname == "evaluations.id"


def test_test_run_test_case_foreign_key():
    foreign_keys = TestRun.__table__.c.test_case_id.foreign_keys

    assert len(foreign_keys) == 1

    foreign_key = next(iter(foreign_keys))

    assert foreign_key.target_fullname == "test_cases.id"
