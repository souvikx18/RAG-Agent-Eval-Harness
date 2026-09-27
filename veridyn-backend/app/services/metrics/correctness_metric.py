from app.services.metrics.base_metric import Metric, MetricResult


class CorrectnessMetric(Metric):

    @property
    def name(self) -> str:
        return "correctness"

    def evaluate(
        self,
        expected_behavior: str | None,
        actual_output: str | None,
    ) -> MetricResult:

        if not actual_output:
            return MetricResult(
                metric_name=self.name,
                score=0.0,
                status="failed",
                explanation="No actual output was produced.",
            )

        if not expected_behavior:
            return MetricResult(
                metric_name=self.name,
                score=1.0,
                status="passed",
                explanation="No expected behavior was provided.",
            )

        expected = expected_behavior.lower().strip()
        actual = actual_output.lower().strip()

        if expected in actual:
            return MetricResult(
                metric_name=self.name,
                score=1.0,
                status="passed",
                explanation=(
                    "Expected behavior was found in the actual output."
                ),
            )

        return MetricResult(
            metric_name=self.name,
            score=0.0,
            status="failed",
            explanation=(
                "Expected behavior was not found in the actual output."
            ),
        )
