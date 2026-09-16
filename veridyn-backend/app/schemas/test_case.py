import uuid

from pydantic import BaseModel, Field


class TestCaseCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=100)
    description: str | None = None
    input_data: str = Field(min_length=1)
    expected_behavior: str | None = None
    is_adversarial: bool = False


class TestCaseResponse(BaseModel):
    id: uuid.UUID
    evaluation_id: uuid.UUID
    name: str
    category: str
    description: str | None = None
    input_data: str
    expected_behavior: str | None = None
    is_adversarial: bool

    model_config = {
        "from_attributes": True
    }