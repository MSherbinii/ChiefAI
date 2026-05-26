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
        """Fetch relevant Life Graph data for this agent. Returns formatted string."""
        ...

    @abstractmethod
    async def handle(self, request: ChatRequest) -> ChatResponse:
        ...
