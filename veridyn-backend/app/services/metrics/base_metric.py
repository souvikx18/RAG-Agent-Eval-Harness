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

    def __post_init__(self) -> None:
        if not self.metric_name.strip():
            raise ValueError("Metric name cannot be empty.")

        if not 0.0 <= self.score <= 1.0:
            raise ValueError(
                "Metric score must be between 0.0 and 1.0."
            )

        if self.status not in {"passed", "failed"}:
            raise ValueError(
                "Metric status must be 'passed' or 'failed'."
            )

        if not self.explanation.strip():
            raise ValueError(
                "Metric explanation cannot be empty."
            )


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
