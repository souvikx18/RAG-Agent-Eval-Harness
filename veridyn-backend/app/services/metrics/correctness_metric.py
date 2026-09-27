from app.services.metrics.base_metric import (
    Metric,
    MetricContext,
    MetricResult,
)


class CorrectnessMetric(Metric):

    @property
    def name(self) -> str:
        return "correctness"

    def evaluate(
        self,
        context: MetricContext,
    ) -> MetricResult:

        if not context.actual_output:
            return MetricResult(
                metric_name=self.name,
                score=0.0,
                status="failed",
                explanation="No actual output was produced.",
            )

        if not context.expected_behavior:
            return MetricResult(
                metric_name=self.name,
                score=1.0,
                status="passed",
                explanation="No expected behavior was provided.",
            )

        expected = context.expected_behavior.lower().strip()
        actual = context.actual_output.lower().strip()

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
