import os
from datetime import datetime, timezone, timedelta
from supabase import create_client
from agents.base import BaseAgent
from models import ChatRequest, ChatResponse
from llm import get_client, AGENT_MODEL

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


class EchoAgent(BaseAgent):
    name = 'Echo'
    description = 'Communication: emails, replies, thread summarization, follow-ups, tone.'

    async def fetch_context(self, user_id: str) -> str:
        if not user_id:
            return 'No user context available.'
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

        cutoff_3d = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        cutoff_2d = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()

        stale = sb.table('lg_communications').select(
            'thread_id, channel, participants, subject, last_message_at, staleness_days'
        ).eq('user_id', user_id).eq('status', 'active') \
         .lte('last_message_at', cutoff_3d) \
         .order('last_message_at', desc=False).limit(10).execute()

        # Compute current staleness at read time (trigger keeps column fresh on writes,
        # but rows not touched since last upsert may drift)
        for t in stale.data or []:
            if t.get('last_message_at'):
                try:
                    lma = datetime.fromisoformat(t['last_message_at'].replace('Z', '+00:00'))
                    t['staleness_days'] = (datetime.now(timezone.utc) - lma).days
                except Exception:
                    t['staleness_days'] = t.get('staleness_days') or 0

        recent = sb.table('lg_communications').select(
            'subject, channel, participants, last_message_at'
        ).eq('user_id', user_id).eq('status', 'active') \
         .gte('last_message_at', cutoff_2d) \
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
        client = get_client()
        context = await self.fetch_context(request.user_id or '')
        messages = [{'role': m.role, 'content': m.content} for m in request.history]
        messages.append({'role': 'user', 'content': request.message})

        response = client.messages.create(
            model=AGENT_MODEL,
            max_tokens=1024,
            system=f'{self.system_prompt}\n\n{context}',
            messages=messages,
        )
        return ChatResponse(reply=response.content[0].text, agent='Echo')
