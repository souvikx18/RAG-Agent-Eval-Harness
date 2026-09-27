from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class MetricResult:
    metric_name: str
    score: float
    status: str
    explanation: str


class Metric(ABC):
    """
    Base abstraction for evaluation metrics.

    Every metric receives the expected behavior and actual output
    and returns a standardized MetricResult.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def evaluate(
        self,
        expected_behavior: str | None,
        actual_output: str | None,
    ) -> MetricResult:
        pass
