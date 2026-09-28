from app.services.metrics.base_metric import Metric, MetricContext, MetricResult


class DummyMetric(Metric):

    @property
    def name(self) -> str:
        return "dummy"

    def evaluate(
        self,
        expected_behavior: str | None | MetricContext = None,
        actual_output: str | None = None,
    ) -> MetricResult:
        return MetricResult(
            metric_name=self.name,
            score=1.0,
            status="passed",
            explanation="Dummy metric passed.",
        )


TestMetric = DummyMetric


def test_metric_result_structure():
    result = MetricResult(
        metric_name="test",
        score=0.75,
        status="passed",
        explanation="Test explanation.",
    )

    assert result.metric_name == "test"
    assert result.score == 0.75
    assert result.status == "passed"
    assert result.explanation == "Test explanation."


def test_metric_abstraction():
    metric = DummyMetric()

    result = metric.evaluate(
        "Expected response",
        "Actual response",
    )

    assert metric.name == "dummy"
    assert result.metric_name == "dummy"
    assert result.score == 1.0
    assert result.status == "passed"


def test_metric_configuration_is_optional():
    metric = DummyMetric()

    metric.configure(
        {
            "threshold": 0.8,
        }
    )


def test_metric_configuration_does_not_change_default_behavior():
    metric = DummyMetric()

    metric.configure({})

    result = metric.evaluate(
        MetricContext(
            expected_behavior="expected",
            actual_output="expected",
            latency_ms=100,
        )
    )

    assert result.score == 1.0
