from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from typing import Any


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


@dataclass
class MetricExecutionResult:
    metric_result: MetricResult
    configuration_version: int
    configuration: dict[str, Any]

    def __post_init__(self) -> None:
        if self.configuration_version < 1:
            raise ValueError(
                "Configuration version must be at least 1."
            )

        if not isinstance(self.configuration, dict):
            raise TypeError(
                "Metric configuration must be a dictionary."
            )

        self.configuration = deepcopy(
            self.configuration
        )


class Metric(ABC):
    """
    Base abstraction for evaluation metrics.
    """

    _configuration_version: int = 1

    def __init__(self) -> None:
        self._configuration_version = 1

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

    def configure(self, config: dict[str, Any]) -> None:
        """
        Configure the metric.

        Metrics that support configuration can override this method.
        """
        return None

    def get_configuration(self) -> dict[str, Any]:
        """
        Return the current metric configuration.
        """
        return {}

    def get_configuration_version(self) -> int:
        """
        Return the current configuration version.
        """
        return self._configuration_version

    def _increment_configuration_version(self) -> None:
        self._configuration_version += 1
