from sqlalchemy import Integer, JSON
from app.models.evaluation_result import EvaluationResult
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


def test_test_run_execution_metadata_columns_are_nullable():
    table = TestRun.__table__

    assert table.c.started_at.nullable is True
    assert table.c.executor_type.nullable is True
    assert table.c.completed_at.nullable is True
    assert table.c.latency_ms.nullable is True


def test_evaluation_result_required_columns_are_not_nullable():
    table = EvaluationResult.__table__

    assert table.c.test_run_id.nullable is False
    assert table.c.metric_name.nullable is False
    assert table.c.status.nullable is False
    assert table.c.configuration_version.nullable is False
    assert table.c.configuration.nullable is False
    assert table.c.created_at.nullable is False


def test_evaluation_result_configuration_metadata():
    table = EvaluationResult.__table__

    # configuration_version metadata
    assert "configuration_version" in table.c
    version_col = table.c.configuration_version
    assert isinstance(version_col.type, Integer)
    assert version_col.nullable is False
    assert version_col.default is not None
    assert version_col.default.arg == 1

    # configuration metadata
    assert "configuration" in table.c
    config_col = table.c.configuration
    assert isinstance(config_col.type, JSON)
    assert config_col.nullable is False


