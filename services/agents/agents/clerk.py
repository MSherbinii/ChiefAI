import os
from agents.base import BaseAgent
from models import ChatRequest, ChatResponse
from llm import get_client, AGENT_MODEL
from tools.admin_tools import get_document_library, find_insurance_number, get_admin_debt, create_admin_draft

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


class ClerkAgent(BaseAgent):
    name = 'Clerk'
    description = 'Admin: insurance letters, bureaucracy, documents, forms, German admin tasks.'

    async def fetch_context(self, user_id: str) -> str:
        if not user_id:
            return 'No document data available.'

        lines = ['=== ADMIN CONTEXT ===']

        # Admin debt overview
        debt = await get_admin_debt(user_id)
        if debt.total_items > 0:
            lines.append(f'ADMIN DEBT: {debt.total_items} items total')
            if debt.overdue:
                lines.append(f'  OVERDUE ({len(debt.overdue)}):')
                for d in debt.overdue[:3]:
                    lines.append(f'    - {d.get("type", "doc")}: {d.get("title", "untitled")} (EXPIRED)')
            if debt.expiring_soon:
                lines.append(f'  EXPIRING SOON ({len(debt.expiring_soon)}):')
                for d in debt.expiring_soon[:3]:
                    days = d.get('days_until_expiry', '?')
                    lines.append(f'    - {d.get("type", "doc")}: {d.get("title", "untitled")} ({days}d remaining)')
        else:
            lines.append('No pending admin items.')

        # Document library summary
        docs = await get_document_library(user_id)
        if docs:
            lines.append(f'DOCUMENTS: {len(docs)} stored')
            doc_types = list(set(d.type for d in docs))
            lines.append(f'  Types: {", ".join(doc_types[:5])}')

        return '\n'.join(lines)

    async def handle(self, request: ChatRequest) -> ChatResponse:
        client = get_client()
        context = await self.fetch_context(request.user_id or '')

        # Detect insurance number request
        msg_lower = request.message.lower()
        if request.user_id and any(kw in msg_lower for kw in ['insurance number', 'versicherungsnummer', 'tk number', 'health insurance']):
            ins_num = await find_insurance_number(request.user_id)
            if ins_num:
                context += f'\nINSURANCE NUMBER (from document library): {ins_num}'

        messages = [{'role': m.role, 'content': m.content} for m in request.history]
        messages.append({'role': 'user', 'content': request.message})

        response = client.messages.create(
            model=AGENT_MODEL,
            max_tokens=1024,
            system=f'{self.system_prompt}\n\n{context}',
            messages=messages,
        )
        return ChatResponse(reply=response.content[0].text, agent='Clerk')
