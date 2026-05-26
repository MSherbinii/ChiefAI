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
    voice_intent: Optional[str] = None  # pre-classified agent hint from voice_intent.intent_to_routing_hint()

class ChatResponse(BaseModel):
    reply: str
    agent: str
    confidence: Optional[str] = None
