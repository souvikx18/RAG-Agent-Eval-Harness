import uuid

from pydantic import BaseModel, Field


class EvaluationCreateRequest(BaseModel):
    agent_version_id: uuid.UUID
    trigger_type: str = Field(
        default="manual",
        max_length=50,
    )


class EvaluationResponse(BaseModel):
    id: uuid.UUID
    agent_version_id: uuid.UUID
    status: str
    trigger_type: str
    summary: str | None = None
    overall_score: float | None = None

    total_runs: int = 0
    passed_runs: int = 0
    failed_runs: int = 0
    average_latency_ms: float = 0.0

    model_config = {
        "from_attributes": True,
    }