from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    login: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    display_name: str | None = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    login: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_expires_in_minutes: int
    refresh_expires_in_days: int


class UserResponse(BaseModel):
    id: int
    login: str
    display_name: str | None = None

    model_config = {"from_attributes": True}
