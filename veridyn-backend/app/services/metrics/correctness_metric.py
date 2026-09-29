from typing import Any

from app.services.metrics.base_metric import (
    Metric,
    MetricContext,
    MetricResult,
)


class CorrectnessMetric(Metric):
    def __init__(self) -> None:
        super().__init__()
        self.case_sensitive = False

    @property
    def name(self) -> str:
        return "correctness"

    def configure(self, config: dict[str, Any]) -> None:
        allowed_keys = {
            "case_sensitive",
        }

        unknown_keys = set(config) - allowed_keys

        if unknown_keys:
            raise ValueError(
                f"Unknown correctness configuration keys: "
                f"{sorted(unknown_keys)}"
            )

        case_sensitive = config.get(
            "case_sensitive",
            self.case_sensitive,
        )

        if not isinstance(case_sensitive, bool):
            raise ValueError(
                "case_sensitive must be a boolean."
            )

        self.case_sensitive = case_sensitive

        self._increment_configuration_version()

    def get_configuration(self) -> dict[str, Any]:
        return {
            "case_sensitive": self.case_sensitive,
        }

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

        expected = context.expected_behavior.strip()
        actual = context.actual_output.strip()

        if not self.case_sensitive:
            expected = expected.lower()
            actual = actual.lower()

        if expected in actual:
            return MetricResult(
                metric_name=self.name,
                score=1.0,
                status="passed",
                explanation="Expected behavior was found in the actual output.",
            )

        return MetricResult(
            metric_name=self.name,
            score=0.0,
            status="failed",
            explanation="Expected behavior was not found in the actual output.",
        )
