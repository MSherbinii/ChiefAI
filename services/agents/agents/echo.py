import anthropic
import os
from datetime import datetime, timezone, timedelta
from supabase import create_client
from agents.base import BaseAgent
from models import ChatRequest, ChatResponse

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


class EchoAgent(BaseAgent):
    name = 'Echo'
    description = 'Communication: emails, replies, thread summarization, follow-ups, tone.'

    async def fetch_context(self, user_id: str) -> str:
        if not user_id:
            return 'No user context available.'
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

        stale = sb.table('lg_communications').select(
            'thread_id, channel, participants, subject, last_message_at, staleness_days'
        ).eq('user_id', user_id).eq('status', 'active') \
         .gte('staleness_days', 3) \
         .order('staleness_days', desc=True).limit(10).execute()

        recent = sb.table('lg_communications').select(
            'subject, channel, participants, last_message_at'
        ).eq('user_id', user_id).eq('status', 'active') \
         .lte('staleness_days', 2) \
         .order('last_message_at', desc=True).limit(5).execute()

        lines = ['=== COMMUNICATION CONTEXT ===']

        if stale.data:
            lines.append(f'STALE THREADS ({len(stale.data)} threads needing attention):')
            for t in stale.data:
                subj = (t.get('subject') or '(no subject)')[:60]
                sender = (t.get('participants') or ['?'])[0][:40]
                lines.append(f'  [{t["staleness_days"]}d] "{subj}" from {sender} via {t["channel"]}')
        else:
            lines.append('No stale threads. Inbox is clear.')

        if recent.data:
            lines.append(f'RECENT ACTIVITY (last 2 days):')
            for t in recent.data:
                subj = (t.get('subject') or '(no subject)')[:60]
                lines.append(f'  "{subj}" — {t["channel"]} — {t["last_message_at"][:10]}')

        return '\n'.join(lines)

    async def handle(self, request: ChatRequest) -> ChatResponse:
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        context = await self.fetch_context(request.user_id or '')
        messages = [{'role': m.role, 'content': m.content} for m in request.history]
        messages.append({'role': 'user', 'content': request.message})

        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=1024,
            system=f'{self.system_prompt}\n\n{context}',
            messages=messages,
        )
        return ChatResponse(reply=response.content[0].text, agent='Echo')
