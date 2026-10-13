from datetime import datetime
import uuid

from pydantic import BaseModel, Field


class TestRunCreateRequest(BaseModel):
    test_case_id: uuid.UUID = Field(..., description="ID of the test case to execute")


class TestRunResponse(BaseModel):
    id: uuid.UUID = Field(..., description="Unique identifier of the test run")
    test_case_id: uuid.UUID = Field(..., description="ID of the parent test case")
    status: str = Field(..., description="Execution status: pending, running, completed, or failed")
    actual_output: str | None = Field(None, description="Output payload returned by the agent")
    result: str | None = Field(None, description="Evaluation result status summary")
    error_message: str | None = Field(None, description="Error message if execution failed")
    latency_ms: int | None = Field(None, description="Total execution round-trip latency in milliseconds")
    started_at: datetime | None = Field(None, description="UTC timestamp when agent execution started")
    completed_at: datetime | None = Field(None, description="UTC timestamp when agent execution completed")
    executor_type: str | None = Field(None, description="Agent executor class name (e.g. HTTPAgentExecutor)")

    model_config = {
        "from_attributes": True
    }


class PaginatedTestRunResponse(BaseModel):
    items: list[TestRunResponse] = Field(..., description="List of test runs for the current page")
    total: int = Field(..., description="Total number of test runs matching the filter criteria")
    skip: int = Field(..., description="Number of skipped records")
    limit: int = Field(..., description="Maximum page size requested")
    has_more: bool = Field(..., description="Whether additional records exist beyond the current page")