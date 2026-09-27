from app.services.metrics.base_metric import Metric
from app.services.metrics.correctness_metric import CorrectnessMetric
from app.services.metrics.latency_metric import LatencyMetric


class MetricRegistry:
    def __init__(self):
        self._metrics: dict[str, Metric] = {}

        self.register(CorrectnessMetric())
        self.register(LatencyMetric())

    def register(self, metric: Metric) -> None:
        if not isinstance(metric, Metric):
            raise TypeError(
                "Only Metric instances can be registered."
            )

        if not metric.name.strip():
            raise ValueError(
                "Metric name cannot be empty."
            )

        if metric.name in self._metrics:
            raise ValueError(
                f"Metric '{metric.name}' is already registered."
            )

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

    def names(self) -> list[str]:
        return list(self._metrics.keys())


metric_registry = MetricRegistry()
