from abc import ABC, abstractmethod
from models import ChatRequest, ChatResponse

class BaseAgent(ABC):
    name: str
    description: str

    @abstractmethod
    async def handle(self, request: ChatRequest) -> ChatResponse:
        ...
