import asyncio
import os
from models import ChatRequest, ChatResponse
from agents import PulseAgent, EchoAgent, ForgeAgent
from llm import get_client, ROUTING_MODEL, AGENT_MODEL
from guardrails import check_input_guardrails, check_output_guardrails, evaluate_response_quality
from memory import save_interaction, get_recent_context, MemoryEntry, save_quality_feedback

AGENTS = [PulseAgent(), EchoAgent(), ForgeAgent()]

ROUTING_SYSTEM = """You are Chief's routing intelligence. Given a user message, decide which specialist to use.

Specialists:
- Pulse: health, fitness, sleep, recovery, gym, nutrition, food, weight, injury
- Echo: emails, communication, professor, reply, draft, message, thread, follow-up
- Forge: thesis, GitHub, code, project, task, startup, deadline, commit, work
- Chief: anything else, general questions, cross-domain, strategy, planning

Respond with ONLY the specialist name (Pulse, Echo, Forge, or Chief). Nothing else."""


async def route_and_handle(request: ChatRequest) -> ChatResponse:
    client = get_client()

    # Voice-intent fast path: skip Haiku routing when caller already classified
    ROUTABLE_AGENTS = {'Pulse', 'Echo', 'Forge', 'Ledger', 'Clerk'}
    if request.voice_intent and request.voice_intent in ROUTABLE_AGENTS:
        agent_name = request.voice_intent
    else:
        routing_response = client.messages.create(
            model=ROUTING_MODEL,
            max_tokens=10,
            system=ROUTING_SYSTEM,
            messages=[{'role': 'user', 'content': request.message}],
        )
        agent_name = routing_response.content[0].text.strip()

    agent = next((a for a in AGENTS if a.name == agent_name), None)

    if agent:
        # 1. Check input guardrails
        input_check = check_input_guardrails(request.message, agent_name)
        if not input_check.passed:
            return ChatResponse(
                reply=f"I can't help with that through {agent_name}. Try asking Chief directly.",
                agent='Chief',
                confidence='high',
            )

        # 2. Get memory context and prepend to history
        memory_context = await get_recent_context(request.user_id or '', agent_name)
        if memory_context:
            # Build ChatMessage-compatible history: memory first, then existing history
            from models import ChatMessage
            memory_msgs = [ChatMessage(role=m['role'], content=m['content']) for m in memory_context]
            request = request.model_copy(update={'history': memory_msgs + list(request.history)})

        # 3. Call agent
        response = await agent.handle(request)

        # 4. Check output guardrails
        output_check = check_output_guardrails(response.reply, agent_name)
        if not output_check.passed and output_check.sanitized_input:
            response = response.model_copy(update={'reply': output_check.sanitized_input})

        # 5. Evaluate quality
        try:
            context_str = await agent.fetch_context(request.user_id or '')
        except Exception:
            context_str = ''
        quality = evaluate_response_quality(request.message, response.reply, context_str, agent_name)

        # 6. Save to memory (non-blocking)
        asyncio.create_task(save_interaction(request.user_id or '', MemoryEntry(
            user_message=request.message,
            agent_response=response.reply,
            agent=agent_name,
            quality_score=quality['score'],
        )))

        # 7. Log quality (async, non-blocking)
        if request.user_id:
            asyncio.create_task(save_quality_feedback(
                request.user_id, agent_name, request.message,
                response.reply, quality['score'], quality['issues'],
            ))

        return response

    # Chief fallback — also apply input guardrails
    input_check = check_input_guardrails(request.message, 'Chief')
    if not input_check.passed:
        return ChatResponse(
            reply="I can't help with that request.",
            agent='Chief',
            confidence='high',
        )

    chief_response = client.messages.create(
        model=AGENT_MODEL,
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
    reply_text = chief_response.content[0].text

    # Output guardrail on Chief too
    output_check = check_output_guardrails(reply_text, 'Chief')
    if not output_check.passed and output_check.sanitized_input:
        reply_text = output_check.sanitized_input

    quality = evaluate_response_quality(request.message, reply_text, '', 'Chief')

    asyncio.create_task(save_interaction(request.user_id or '', MemoryEntry(
        user_message=request.message,
        agent_response=reply_text,
        agent='Chief',
        quality_score=quality['score'],
    )))

    if request.user_id:
        asyncio.create_task(save_quality_feedback(
            request.user_id, 'Chief', request.message,
            reply_text, quality['score'], quality['issues'],
        ))

    return ChatResponse(reply=reply_text, agent='Chief', confidence='medium')
