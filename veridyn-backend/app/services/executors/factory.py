from app.services.executors.agent_executor import AgentExecutor
from app.services.executors.placeholder_executor import (
    PlaceholderAgentExecutor,
)


def get_agent_executor(
    endpoint: str | None = None,
) -> AgentExecutor:

    return PlaceholderAgentExecutor()
