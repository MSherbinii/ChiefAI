from agents.base import BaseAgent
from models import ChatRequest, ChatResponse
import anthropic
import os

class EchoAgent(BaseAgent):
    name = 'Echo'
    description = 'Communication: emails, replies, thread summarization, follow-ups, tone.'

    async def handle(self, request: ChatRequest) -> ChatResponse:
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        messages = [{'role': m.role, 'content': m.content} for m in request.history]
        messages.append({'role': 'user', 'content': request.message})

        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=1024,
            system=(
                "You are Echo, Chief's communication agent. "
                "Help draft emails, summarize threads, and manage communication tasks. "
                "Match the user's tone. "
                "When drafting emails, always show a preview and note it needs approval before sending."
            ),
            messages=messages,
        )
        return ChatResponse(reply=response.content[0].text, agent='Echo')
