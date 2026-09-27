from app.services.metrics.base_metric import Metric, MetricResult


class LatencyMetric(Metric):

    @property
    def name(self) -> str:
        return "latency"

    def evaluate(
        self,
        expected_behavior: str | None,
        actual_output: str | None,
        latency_ms: int | None = None,
    ) -> MetricResult:

        if latency_ms is None:
            return MetricResult(
                metric_name=self.name,
                score=0.0,
                status="failed",
                explanation="Latency was not recorded.",
            )

        if latency_ms <= 500:
            return MetricResult(
                metric_name=self.name,
                score=1.0,
                status="passed",
                explanation="Latency is within the target range.",
            )

        if latency_ms <= 1000:
            return MetricResult(
                metric_name=self.name,
                score=0.75,
                status="passed",
                explanation=(
                    "Latency is acceptable but above the target range."
                ),
            )

        if latency_ms <= 2000:
            return MetricResult(
                metric_name=self.name,
                score=0.5,
                status="failed",
                explanation="Latency is relatively high.",
            )

        return MetricResult(
            metric_name=self.name,
            score=0.0,
            status="failed",
            explanation="Latency exceeds the target range.",
        )
