from agents.base import BaseAgent
from models import ChatRequest, ChatResponse
import anthropic
import os

class PulseAgent(BaseAgent):
    name = 'Pulse'
    description = 'Health and fitness: recovery, sleep, gym planning, nutrition, weight.'

    async def handle(self, request: ChatRequest) -> ChatResponse:
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        messages = [{'role': m.role, 'content': m.content} for m in request.history]
        messages.append({'role': 'user', 'content': request.message})

        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=512,
            system=(
                "You are Pulse, Chief's health and fitness agent. "
                "You're warm, direct, and knowledgeable about recovery, training, and nutrition. "
                "Speak like a mentor who knows the user's body well. "
                "Keep responses concise — 2-4 sentences unless detail is needed. "
                "Be honest about confidence levels when estimating."
            ),
            messages=messages,
        )
        return ChatResponse(reply=response.content[0].text, agent='Pulse')
