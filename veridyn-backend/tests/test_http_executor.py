from unittest.mock import patch, MagicMock
from app.services.executors.http_executor import (
    HTTPAgentExecutor,
)
from app.services.executors.placeholder_executor import (
    PlaceholderAgentExecutor,
)
from app.services.executors.agent_executor import (
    AgentExecutionRequest,
    AgentExecutionResponse,
)
from app.services.executors.factory import get_agent_executor


def test_http_executor_requires_endpoint():

    executor = HTTPAgentExecutor()

    request = AgentExecutionRequest(
        input_data="Hello",
        endpoint=None,
    )

    response = executor.execute(request)

    assert response.error == (
        "Agent endpoint is not configured."
    )

    assert response.output == ""


def test_factory_selection():
    """Verify factory routes based on presence of endpoint."""
    executor_placeholder = get_agent_executor(endpoint=None)
    assert isinstance(executor_placeholder, PlaceholderAgentExecutor)

    executor_empty = get_agent_executor(endpoint="")
    assert isinstance(executor_empty, PlaceholderAgentExecutor)

    executor_http = get_agent_executor(endpoint="https://api.agent.ai/chat")
    assert isinstance(executor_http, HTTPAgentExecutor)


@patch("httpx.post")
def test_http_executor_successful_response(mock_post):
    """Verify HTTP POST request formatting, parsing of output field, and latency measurement."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"output": "Agent response from API"}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    executor = HTTPAgentExecutor()
    request = AgentExecutionRequest(
        input_data="Test input prompt",
        endpoint="https://agent.enterprise.internal/run",
    )

    response = executor.execute(request)

    mock_post.assert_called_once_with(
        "https://agent.enterprise.internal/run",
        json={"input": "Test input prompt"},
        timeout=30.0,
    )
    assert response.output == "Agent response from API"
    assert response.latency_ms >= 0
    assert response.error is None


@patch("httpx.post")
def test_http_executor_fallback_output(mock_post):
    """Verify fallback string serialization when output key is missing in response JSON."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"message": "success", "result": 42}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    executor = HTTPAgentExecutor()
    request = AgentExecutionRequest(
        input_data="Calculate",
        endpoint="https://agent.enterprise.internal/run",
    )

    response = executor.execute(request)

    assert "{'message': 'success', 'result': 42}" in response.output
    assert response.error is None


@patch("httpx.post")
def test_http_executor_captures_exceptions(mock_post):
    """Verify network timeouts and HTTP errors are trapped without unhandled exceptions."""
    import httpx

    mock_post.side_effect = httpx.ConnectTimeout("Connection timed out")

    executor = HTTPAgentExecutor()
    request = AgentExecutionRequest(
        input_data="Test timeout",
        endpoint="https://unreachable.endpoint/run",
    )

    response = executor.execute(request)

    assert response.output == ""
    assert "Connection timed out" in response.error
    assert response.latency_ms >= 0
