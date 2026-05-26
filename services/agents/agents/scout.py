import os
import httpx
from agents.base import BaseAgent
from models import ChatRequest, ChatResponse
from llm import get_client, AGENT_MODEL


class ScoutAgent(BaseAgent):
    name = 'Scout'
    description = 'Research: market intelligence, comparisons, travel, regulations, German courses, competitive analysis.'

    async def fetch_context(self, user_id: str) -> str:
        # Scout primarily uses web search + Life Graph entities
        # Provide entity context from the knowledge graph
        if not user_id:
            return ''
        try:
            from semantic_search import search_entities
            # No specific query here — entity context loaded per-request in build_full_context
            return '=== SCOUT CONTEXT ===\nI can research topics and find information for you.'
        except Exception:
            return ''

    async def handle(self, request: ChatRequest) -> ChatResponse:
        client = get_client()
        context = await self.build_full_context(request.user_id or '', request.message)
        messages = [{'role': m.role, 'content': m.content} for m in request.history]
        messages.append({'role': 'user', 'content': request.message})

        response = client.messages.create(
            model=AGENT_MODEL,
            max_tokens=1024,
            system=f'{self.system_prompt}\n\n{context}',
            messages=messages,
        )
        return ChatResponse(reply=response.content[0].text, agent='Scout')
