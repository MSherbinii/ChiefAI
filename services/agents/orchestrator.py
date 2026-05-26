import anthropic
import os
from models import ChatRequest, ChatResponse
from agents import PulseAgent, EchoAgent, ForgeAgent

AGENTS = [PulseAgent(), EchoAgent(), ForgeAgent()]

ROUTING_SYSTEM = """You are Chief's routing intelligence. Given a user message, decide which specialist to use.

Specialists:
- Pulse: health, fitness, sleep, recovery, gym, nutrition, food, weight, injury
- Echo: emails, communication, professor, reply, draft, message, thread, follow-up
- Forge: thesis, GitHub, code, project, task, startup, deadline, commit, work
- Chief: anything else, general questions, cross-domain, strategy, planning

Respond with ONLY the specialist name (Pulse, Echo, Forge, or Chief). Nothing else."""


async def route_and_handle(request: ChatRequest) -> ChatResponse:
    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    routing_response = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=10,
        system=ROUTING_SYSTEM,
        messages=[{'role': 'user', 'content': request.message}],
    )
    agent_name = routing_response.content[0].text.strip()

    agent = next((a for a in AGENTS if a.name == agent_name), None)
    if agent:
        return await agent.handle(request)

    chief_response = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=1024,
        system=(
            "You are Chief, a personal life operating system. "
            "You're a trusted advisor — warm, direct, and intelligent. "
            "You help manage health, finances, work, communication, and admin. "
            "Keep responses concise and actionable. "
            "Never say 'As an AI' — just be Chief."
        ),
        messages=[{'role': m.role, 'content': m.content} for m in request.history] +
                 [{'role': 'user', 'content': request.message}],
    )
    return ChatResponse(reply=chief_response.content[0].text, agent='Chief')
