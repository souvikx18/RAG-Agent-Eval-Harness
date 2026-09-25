import time

from app.services.executors.agent_executor import (
    AgentExecutionRequest,
    AgentExecutionResponse,
    AgentExecutor,
)


class PlaceholderAgentExecutor(AgentExecutor):

    def execute(
        self,
        request: AgentExecutionRequest,
    ) -> AgentExecutionResponse:

        start_time = time.perf_counter()

        output = (
            f"Agent received input: "
            f"{request.input_data}"
        )

        latency_ms = int(
            (time.perf_counter() - start_time) * 1000
        )

        return AgentExecutionResponse(
            output=output,
            latency_ms=latency_ms,
        )
