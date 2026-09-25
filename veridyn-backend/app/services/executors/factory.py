from app.services.executors.agent_executor import AgentExecutor
from app.services.executors.http_executor import (
    HTTPAgentExecutor,
)
from app.services.executors.placeholder_executor import (
    PlaceholderAgentExecutor,
)


def get_agent_executor(
    endpoint: str | None = None,
) -> AgentExecutor:

    if endpoint:
        return HTTPAgentExecutor()

    return PlaceholderAgentExecutor()
