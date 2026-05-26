from pydantic import BaseModel
from typing import Optional

class ChatMessage(BaseModel):
    role: str  # 'user' | 'assistant'
    content: str
    agent: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    agent: str
    confidence: Optional[str] = None
