import uuid

from pydantic import BaseModel, Field


class AgentCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    framework: str | None = Field(default=None, max_length=100)


class AgentResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    description: str | None = None
    framework: str | None = None
    is_active: bool

    model_config = {
        "from_attributes": True
    }