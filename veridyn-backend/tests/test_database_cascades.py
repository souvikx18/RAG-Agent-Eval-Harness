from app.models.test_case import TestCase
from app.models.test_run import TestRun


def test_test_case_evaluation_foreign_key_has_cascade():
    foreign_key = next(
        iter(TestCase.__table__.c.evaluation_id.foreign_keys)
    )

    assert foreign_key.ondelete == "CASCADE"


def test_test_run_test_case_foreign_key_has_cascade():
    foreign_key = next(
        iter(TestRun.__table__.c.test_case_id.foreign_keys)
    )

    assert foreign_key.ondelete == "CASCADE"
