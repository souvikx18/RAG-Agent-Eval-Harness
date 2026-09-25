import time

import httpx

from app.services.executors.agent_executor import (
    AgentExecutionRequest,
    AgentExecutionResponse,
    AgentExecutor,
)


class HTTPAgentExecutor(AgentExecutor):

    def execute(
        self,
        request: AgentExecutionRequest,
    ) -> AgentExecutionResponse:

        if not request.endpoint:
            return AgentExecutionResponse(
                output="",
                latency_ms=0,
                error="Agent endpoint is not configured.",
            )

        start_time = time.perf_counter()

        try:
            response = httpx.post(
                request.endpoint,
                json={
                    "input": request.input_data,
                },
                timeout=30.0,
            )

            latency_ms = int(
                (time.perf_counter() - start_time) * 1000
            )

            response.raise_for_status()

            data = response.json()

            output = data.get("output")

            if output is None:
                output = str(data)

            return AgentExecutionResponse(
                output=str(output),
                latency_ms=latency_ms,
            )

        except Exception as exc:
            latency_ms = int(
                (time.perf_counter() - start_time) * 1000
            )

            return AgentExecutionResponse(
                output="",
                latency_ms=latency_ms,
                error=str(exc),
            )
