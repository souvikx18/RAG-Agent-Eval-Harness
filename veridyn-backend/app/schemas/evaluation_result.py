import uuid

from pydantic import BaseModel, Field


class EvaluationResultCreateRequest(BaseModel):
    metric_name: str = Field(min_length=1, max_length=100)
    score: float | None = None
    status: str = Field(min_length=1, max_length=50)
    explanation: str | None = None


class EvaluationResultResponse(BaseModel):
    id: uuid.UUID
    test_run_id: uuid.UUID
    metric_name: str
    score: float | None = None
    status: str
    explanation: str | None = None

    model_config = {
        "from_attributes": True
    }