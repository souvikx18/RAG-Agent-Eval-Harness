from pydantic import BaseModel, EmailStr, Field
import uuid

class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str | None = None
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None = None
    is_active: bool

    model_config = {
        "from_attributes": True
    }