from agents.base import BaseAgent
from models import ChatRequest, ChatResponse
import anthropic
import os

class ForgeAgent(BaseAgent):
    name = 'Forge'
    description = 'Projects: thesis, GitHub repos, startup tasks, Notion, deliverables, velocity.'

    async def handle(self, request: ChatRequest) -> ChatResponse:
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        messages = [{'role': m.role, 'content': m.content} for m in request.history]
        messages.append({'role': 'user', 'content': request.message})

        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=512,
            system=(
                "You are Forge, Chief's projects and work agent. "
                "Track progress, identify blockers, help prioritize. "
                "Be direct about the most valuable next action. "
                "Reference concrete data (commits, deadlines, task counts) when available."
            ),
            messages=messages,
        )
        return ChatResponse(reply=response.content[0].text, agent='Forge')
