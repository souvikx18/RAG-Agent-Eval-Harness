import uuid

from pydantic import BaseModel


class ExecutionTraceCreateRequest(BaseModel):
    trace_type: str
    name: str | None = None
    input_data: str | None = None
    output_data: str | None = None
    error_message: str | None = None
    latency_ms: int | None = None


class ExecutionTraceResponse(BaseModel):
    id: uuid.UUID
    test_run_id: uuid.UUID
    trace_type: str
    name: str | None = None
    input_data: str | None = None
    output_data: str | None = None
    error_message: str | None = None
    latency_ms: int | None = None

    model_config = {
        "from_attributes": True
    }