from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class MetricContext:
    expected_behavior: str | None
    actual_output: str | None
    latency_ms: int | None


@dataclass
class MetricResult:
    metric_name: str
    score: float
    status: str
    explanation: str


class Metric(ABC):
    """
    Base abstraction for evaluation metrics.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def evaluate(
        self,
        context: MetricContext,
    ) -> MetricResult:
        pass
