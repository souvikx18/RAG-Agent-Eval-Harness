import uuid

from pydantic import BaseModel


class DeploymentGateResponse(BaseModel):
    id: uuid.UUID
    evaluation_id: uuid.UUID
    decision: str
    overall_score: float | None = None
    reason: str | None = None

    model_config = {
        "from_attributes": True
    }