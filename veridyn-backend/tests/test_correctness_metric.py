from app.services.metrics.correctness_metric import CorrectnessMetric


def test_correctness_metric_passes_when_expected_behavior_is_found():
    metric = CorrectnessMetric()

    result = metric.evaluate(
        "helpful greeting",
        "Hello! This is a helpful greeting.",
    )

    assert metric.name == "correctness"
    assert result.metric_name == "correctness"
    assert result.score == 1.0
    assert result.status == "passed"


def test_correctness_metric_fails_when_expected_behavior_is_missing():
    metric = CorrectnessMetric()

    result = metric.evaluate(
        "helpful greeting",
        "I cannot help with that.",
    )

    assert result.score == 0.0
    assert result.status == "failed"


def test_correctness_metric_fails_without_actual_output():
    metric = CorrectnessMetric()

    result = metric.evaluate(
        "helpful greeting",
        None,
    )

    assert result.score == 0.0
    assert result.status == "failed"


def test_correctness_metric_passes_without_expected_behavior():
    metric = CorrectnessMetric()

    result = metric.evaluate(
        None,
        "Any response",
    )

    assert result.score == 1.0
    assert result.status == "passed"


def test_correctness_metric_is_case_insensitive():
    metric = CorrectnessMetric()

    result = metric.evaluate(
        "Helpful Greeting",
        "This is a HELPFUL GREETING.",
    )

    assert result.score == 1.0
    assert result.status == "passed"
