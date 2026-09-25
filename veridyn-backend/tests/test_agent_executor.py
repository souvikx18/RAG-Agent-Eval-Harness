from app.services.executors.agent_executor import (
    AgentExecutionRequest,
    AgentExecutionResponse,
)
from app.services.executors.factory import get_agent_executor
from app.services.executors.placeholder_executor import (
    PlaceholderAgentExecutor,
)


def test_placeholder_executor():

    executor = get_agent_executor()

    request = AgentExecutionRequest(
        input_data="Hello",
    )

    response = executor.execute(request)

    assert isinstance(
        response,
        AgentExecutionResponse,
    )

    assert response.output == (
        "Agent received input: Hello"
    )

    assert response.latency_ms >= 0

    assert response.error is None


def test_placeholder_executor_direct():
    """Verify PlaceholderAgentExecutor handles requests with optional metadata."""
    executor = PlaceholderAgentExecutor()

    request = AgentExecutionRequest(
        input_data="What is the refund policy?",
        endpoint="https://api.myagent.ai/v1/chat",
        config_hash="abc123hash",
    )

    response = executor.execute(request)

    assert isinstance(response, AgentExecutionResponse)
    assert response.output == "Agent received input: What is the refund policy?"
    assert response.latency_ms >= 0
    assert response.error is None
