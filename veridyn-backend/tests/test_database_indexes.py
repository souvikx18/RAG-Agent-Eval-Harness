from app.models.test_case import TestCase
from app.models.test_run import TestRun


def test_test_case_evaluation_id_has_index():
    column = TestCase.__table__.c.evaluation_id

    assert column.index is True


def test_test_run_test_case_id_has_index():
    column = TestRun.__table__.c.test_case_id

    assert column.index is True
