"""
Real tool implementations for Echo (communication) agent.
Reads Gmail threads, drafts emails, tracks staleness.
"""
import os
import httpx
from datetime import datetime, timezone, timedelta
from supabase import create_client
from pydantic import BaseModel
from typing import Optional

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


class EmailDraft(BaseModel):
    to: str
    subject: str
    body: str
    thread_id: Optional[str] = None
    context_sources: list[str] = []


class CommsToolResult(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


async def get_stale_threads(user_id: str, min_days: int = 3, limit: int = 10) -> list[dict]:
    """Get email threads that need attention."""
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=min_days)).isoformat()

        result = sb.table('lg_communications') \
            .select('thread_id, subject, participants, channel, last_message_at, staleness_days') \
            .eq('user_id', user_id) \
            .eq('status', 'active') \
            .lte('last_message_at', cutoff) \
            .order('last_message_at', desc=False) \
            .limit(limit) \
            .execute()

        threads = []
        for t in (result.data or []):
            lma = t.get('last_message_at', '')
            days_stale = 0
            if lma:
                try:
                    dt = datetime.fromisoformat(lma.replace('Z', '+00:00'))
                    days_stale = (datetime.now(timezone.utc) - dt).days
                except Exception:
                    days_stale = t.get('staleness_days', 0) or 0

            threads.append({
                'thread_id': t['thread_id'],
                'subject': t.get('subject', '(no subject)'),
                'from': (t.get('participants') or ['?'])[0],
                'channel': t.get('channel', 'unknown'),
                'days_stale': days_stale,
                'urgency': 'high' if days_stale >= 7 else 'medium' if days_stale >= 3 else 'low',
            })

        return sorted(threads, key=lambda x: x['days_stale'], reverse=True)
    except Exception as e:
        return [{'error': str(e)}]


async def create_draft_in_queue(user_id: str, draft: EmailDraft) -> CommsToolResult:
    """
    Save an email draft to the approval queue.
    User must approve before it's sent.
    """
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        sb.table('approval_queue').insert({
            'user_id': user_id,
            'agent': 'Echo',
            'action_type': 'draft_email',
            'risk_level': 'approve',
            'title': f'Email draft: {draft.subject[:50]}',
            'description': f'To: {draft.to}\n\n{draft.body[:200]}...' if len(draft.body) > 200 else f'To: {draft.to}\n\n{draft.body}',
            'payload': {
                'to': draft.to,
                'subject': draft.subject,
                'body': draft.body,
                'thread_id': draft.thread_id,
            },
            'context_capsule': {
                'sources': draft.context_sources,
                'reasoning': 'Draft created based on thread history and communication patterns',
                'confidence': 'MEDIUM',
            },
            'status': 'pending',
        }).execute()
        return CommsToolResult(
            success=True,
            message=f'Draft queued for approval: "{draft.subject}"',
            data={'to': draft.to, 'subject': draft.subject}
        )
    except Exception as e:
        return CommsToolResult(success=False, message=str(e))


async def mark_thread_resolved(user_id: str, thread_id: str) -> CommsToolResult:
    """Mark a communication thread as resolved."""
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        sb.table('lg_communications') \
            .update({'status': 'resolved', 'updated_at': datetime.now(timezone.utc).isoformat()}) \
            .eq('user_id', user_id) \
            .eq('thread_id', thread_id) \
            .execute()
        return CommsToolResult(success=True, message=f'Thread {thread_id[:20]} marked resolved')
    except Exception as e:
        return CommsToolResult(success=False, message=str(e))
