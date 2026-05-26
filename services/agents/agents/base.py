from abc import ABC, abstractmethod
from models import ChatRequest, ChatResponse
import yaml, os


def load_role(agent_name: str) -> dict:
    roles_dir = os.path.join(os.path.dirname(__file__), '..', 'roles')
    path = os.path.join(roles_dir, f'{agent_name.lower()}.yaml')
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return yaml.safe_load(f)


class BaseAgent(ABC):
    name: str
    description: str

    def __init__(self):
        self.role = load_role(self.name)
        self.system_prompt = self.role.get('system_prompt', '').strip()

    @abstractmethod
    async def fetch_context(self, user_id: str) -> str:
        """Fetch domain-specific Life Graph data. Returns formatted string."""
        ...

    async def fetch_rag_context(self, user_id: str, query: str) -> str:
        """
        Semantic RAG context injection.
        Searches Life Graph entities and communications relevant to the query.
        Returns empty string gracefully if RAG fails (non-blocking).
        """
        if not user_id or not query:
            return ''
        try:
            from semantic_search import rag_context_for_query
            return await rag_context_for_query(user_id, query)
        except Exception:
            return ''

    async def build_full_context(self, user_id: str, query: str) -> str:
        """
        Combines domain context + RAG context.
        Called by handle() to build the complete system prompt context.
        """
        domain_ctx = await self.fetch_context(user_id)
        rag_ctx = await self.fetch_rag_context(user_id, query)

        parts = []
        if domain_ctx:
            parts.append(domain_ctx)
        if rag_ctx:
            parts.append(f'\nSEMANTIC CONTEXT (relevant to your query):\n{rag_ctx}')

        return '\n'.join(parts)

    @abstractmethod
    async def handle(self, request: ChatRequest) -> ChatResponse:
        ...
