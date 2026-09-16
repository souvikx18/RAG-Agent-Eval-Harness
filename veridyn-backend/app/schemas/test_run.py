import uuid

from pydantic import BaseModel


class TestRunResponse(BaseModel):
    id: uuid.UUID
    test_case_id: uuid.UUID
    status: str
    actual_output: str | None = None
    result: str | None = None
    error_message: str | None = None
    latency_ms: int | None = None

    model_config = {
        "from_attributes": True
    }