from app.services.metrics.base_metric import Metric
from app.services.metrics.correctness_metric import CorrectnessMetric
from app.services.metrics.latency_metric import LatencyMetric


class MetricRegistry:
    """
    Central registry for available evaluation metrics.
    """

    def __init__(self) -> None:
        self._metrics: dict[str, Metric] = {}

        self.register(CorrectnessMetric())
        self.register(LatencyMetric())

    def register(self, metric: Metric) -> None:
        self._metrics[metric.name] = metric

    def get(self, metric_name: str) -> Metric:
        try:
            return self._metrics[metric_name]
        except KeyError:
            raise ValueError(
                f"Unknown metric: {metric_name}"
            )

    def all(self) -> list[Metric]:
        return list(self._metrics.values())


metric_registry = MetricRegistry()
