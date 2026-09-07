"""Request and response models for the chat API."""

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["human", "user", "ai", "assistant"]
    content: str

class ChatRequest(BaseModel):
    message: str
    provider: Literal["gmail", "outlook", "yahoo"]
    credentials: dict[str, str] = Field(default_factory=dict)
    session_id: str = "default"
    history: list[ChatMessage] = Field(default_factory=list)

class ChatResponse(BaseModel):
    response: str
