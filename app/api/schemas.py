from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    message: str
    provider: str  # "gmail", "outlook", or "yahoo"
    credentials: dict # API keys or file paths
    history: Optional[List[dict]] = []

class ChatResponse(BaseModel):
    response: str
