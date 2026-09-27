from app.models.test_case import TestCase
from app.models.test_run import TestRun


def test_test_case_required_columns_are_not_nullable():
    table = TestCase.__table__

    assert table.c.evaluation_id.nullable is False
    assert table.c.name.nullable is False
    assert table.c.category.nullable is False
    assert table.c.input_data.nullable is False
    assert table.c.is_adversarial.nullable is False


def test_test_run_required_columns_are_not_nullable():
    table = TestRun.__table__

    assert table.c.test_case_id.nullable is False
    assert table.c.status.nullable is False
