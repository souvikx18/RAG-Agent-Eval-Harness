from typing import Any

from app.services.metrics.base_metric import Metric, MetricContext, MetricResult


class LatencyMetric(Metric):
    def __init__(self) -> None:
        self.fast_threshold_ms = 500
        self.acceptable_threshold_ms = 1000
        self.high_threshold_ms = 2000

    @property
    def name(self) -> str:
        return "latency"

    def configure(self, config: dict[str, Any]) -> None:
        allowed_keys = {
            "fast_threshold_ms",
            "acceptable_threshold_ms",
            "high_threshold_ms",
        }

        unknown_keys = set(config) - allowed_keys

        if unknown_keys:
            raise ValueError(
                f"Unknown latency configuration keys: "
                f"{sorted(unknown_keys)}"
            )

        fast_threshold = config.get(
            "fast_threshold_ms",
            self.fast_threshold_ms,
        )

        acceptable_threshold = config.get(
            "acceptable_threshold_ms",
            self.acceptable_threshold_ms,
        )

        high_threshold = config.get(
            "high_threshold_ms",
            self.high_threshold_ms,
        )

        if not isinstance(fast_threshold, int):
            raise ValueError(
                "fast_threshold_ms must be an integer."
            )

        if not isinstance(acceptable_threshold, int):
            raise ValueError(
                "acceptable_threshold_ms must be an integer."
            )

        if not isinstance(high_threshold, int):
            raise ValueError(
                "high_threshold_ms must be an integer."
            )

        if fast_threshold < 0:
            raise ValueError(
                "fast_threshold_ms cannot be negative."
            )

        if acceptable_threshold <= fast_threshold:
            raise ValueError(
                "acceptable_threshold_ms must be greater than fast_threshold_ms."
            )

        if high_threshold <= acceptable_threshold:
            raise ValueError(
                "high_threshold_ms must be greater than acceptable_threshold_ms."
            )

        self.fast_threshold_ms = fast_threshold
        self.acceptable_threshold_ms = acceptable_threshold
        self.high_threshold_ms = high_threshold

    def get_configuration(self) -> dict[str, Any]:
        return {
            "fast_threshold_ms": self.fast_threshold_ms,
            "acceptable_threshold_ms": self.acceptable_threshold_ms,
            "high_threshold_ms": self.high_threshold_ms,
        }

    def evaluate(
        self,
        context: MetricContext,
    ) -> MetricResult:
        if context.latency_ms is None:
            return MetricResult(
                metric_name=self.name,
                score=0.0,
                status="failed",
                explanation="Latency was not recorded.",
            )

        if context.latency_ms <= self.fast_threshold_ms:
            return MetricResult(
                metric_name=self.name,
                score=1.0,
                status="passed",
                explanation="Latency is within the target range.",
            )

        if context.latency_ms <= self.acceptable_threshold_ms:
            return MetricResult(
                metric_name=self.name,
                score=0.75,
                status="passed",
                explanation="Latency is acceptable but above the target range.",
            )

        if context.latency_ms <= self.high_threshold_ms:
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
