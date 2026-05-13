from datetime import datetime

from pydantic import BaseModel, Field


class ChatCreateRequest(BaseModel):
    title: str = Field(default="New Chat", min_length=1, max_length=150)


class ChatResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
