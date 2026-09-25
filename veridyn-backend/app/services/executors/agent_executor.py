from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AgentExecutionRequest:
    input_data: str
    endpoint: str | None = None
    config_hash: str | None = None


@dataclass
class AgentExecutionResponse:
    output: str
    latency_ms: int
    error: str | None = None


class AgentExecutor(ABC):

    @abstractmethod
    def execute(
        self,
        request: AgentExecutionRequest,
    ) -> AgentExecutionResponse:
        pass
