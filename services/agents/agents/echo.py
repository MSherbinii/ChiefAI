import os
from datetime import datetime, timezone, timedelta
from supabase import create_client
from agents.base import BaseAgent
from models import ChatRequest, ChatResponse
from llm import get_client, AGENT_MODEL
from tools.comms_tools import get_stale_threads, create_draft_in_queue
from response_models import CommunicationAnalysis
from pydantic_agents import run_structured

_STALE_THREAD_KEYWORDS = [
    "stale", "threads", "emails need",
    "what needs attention", "follow up",
    "inbox status", "comms status",
    "unanswered", "awaiting reply",
]

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

        if recent.data:
            lines.append(f'RECENT EMAILS (last 2 days — {len(recent.data)} threads):')
            for t in recent.data:
                subj = (t.get('subject') or '(no subject)')[:60]
                lines.append(f'  "{subj}" — {t["channel"]} — {t["last_message_at"][:10]}')

        if not stale.data and not recent.data:
            lines.append('No emails synced yet. Gmail not connected or sync pending.')
        elif not stale.data:
            lines.append('No stale threads — inbox is current.')

        lines.append('\nIMPORTANT: The above IS the user\'s real email data from their Gmail account. Use it to answer.')

        return '\n'.join(lines)

    async def handle(self, request: ChatRequest) -> ChatResponse:
        msg_lower = request.message.lower()
        context = await self.build_full_context(request.user_id or '', request.message)

        # Enrich context with tool-sourced stale thread details (urgency breakdown)
        if request.user_id:
            threads = await get_stale_threads(request.user_id, min_days=3, limit=5)
            high_urgency = [t for t in threads if t.get('urgency') == 'high' and 'error' not in t]
            if high_urgency:
                context += f'\nHIGH-URGENCY THREADS ({len(high_urgency)} threads stale 7+ days):'
                for t in high_urgency:
                    context += f'\n  [{t["days_stale"]}d] "{t["subject"][:60]}" from {t["from"][:40]}'

        # --- Structured output path for stale-thread / inbox-status queries ---
        use_structured = request.user_id and any(
            kw in msg_lower for kw in _STALE_THREAD_KEYWORDS
        )
        if use_structured:
            try:
                result: CommunicationAnalysis = await run_structured(
                    CommunicationAnalysis,
                    self.system_prompt,
                    request.message,
                    context=context,
                )
                parts = [result.summary]
                if result.stale_count:
                    parts.append(f'{result.stale_count} thread(s) need attention.')
                if result.most_urgent:
                    parts.append(f'Most urgent: "{result.most_urgent}"')
                parts.append(f'→ {result.action}')
                reply = '\n\n'.join(parts)
                return ChatResponse(reply=reply, agent='Echo', confidence=result.confidence)
            except Exception:
                pass  # Fall through to standard LLM path

        # --- Standard LLM path ---
        client = get_client()
        messages = [{'role': m.role, 'content': m.content} for m in request.history]

        # Inject context as an assistant message so the model treats it as known data
        # This works better than system prompt for Haiku which over-refuses email access claims
        if context and 'RECENT EMAILS' in context or 'STALE THREADS' in context:
            messages.append({
                'role': 'assistant',
                'content': f'[Checking Gmail...]\n\n{context}\n\n[Data loaded. Responding based on real email data above.]'
            })

        messages.append({'role': 'user', 'content': request.message})

        from llm import BRIEF_MODEL  # Use Sonnet for Echo — Haiku over-refuses email access
        response = client.messages.create(
            model=BRIEF_MODEL,
            max_tokens=1024,
            system=self.system_prompt,
            messages=messages,
        )
        return ChatResponse(reply=response.content[0].text, agent='Echo')
