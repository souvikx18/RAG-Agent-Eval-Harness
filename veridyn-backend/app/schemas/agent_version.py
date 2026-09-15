import uuid

from pydantic import BaseModel, Field


class AgentVersionCreateRequest(BaseModel):
    version: str = Field(min_length=1, max_length=100)
    description: str | None = None
    endpoint: str | None = Field(default=None, max_length=500)
    config_hash: str | None = Field(default=None, max_length=128)


class AgentVersionResponse(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    version: str
    description: str | None = None
    endpoint: str | None = None
    config_hash: str | None = None
    is_active: bool

    model_config = {
        "from_attributes": True
    }