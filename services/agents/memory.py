"""
Memory and context management for Chief agents.
Appends interactions to chat_messages and builds running context.
"""
import os
from datetime import datetime, timezone
from supabase import create_client
from pydantic import BaseModel
from typing import Optional

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


class MemoryEntry(BaseModel):
    user_message: str
    agent_response: str
    agent: str
    quality_score: Optional[float] = None
    context_used: Optional[str] = None


async def save_interaction(user_id: str, entry: MemoryEntry) -> None:
    """Save interaction to chat_messages for future context."""
    if not user_id:
        return
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        sb.table('chat_messages').insert({
            'user_id': user_id,
            'role': 'user',
            'content': entry.user_message,
            'agent': entry.agent,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }).execute()
        sb.table('chat_messages').insert({
            'user_id': user_id,
            'role': 'assistant',
            'content': entry.agent_response,
            'agent': entry.agent,
            'metadata': {'quality_score': entry.quality_score},
            'created_at': datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception:
        pass


async def get_recent_context(user_id: str, agent: str, limit: int = 5) -> list[dict]:
    """Fetch last N interactions for this agent to build conversation context."""
    if not user_id:
        return []
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        result = sb.table('chat_messages') \
            .select('role, content, agent') \
            .eq('user_id', user_id) \
            .eq('agent', agent) \
            .order('created_at', desc=True) \
            .limit(limit * 2) \
            .execute()
        # Return in chronological order
        messages = list(reversed(result.data or []))
        return [{'role': m['role'], 'content': m['content']} for m in messages]
    except Exception:
        return []


async def save_quality_feedback(
    user_id: str,
    agent: str,
    message: str,
    response: str,
    quality_score: float,
    issues: list[str]
) -> None:
    """
    Save quality evaluation result.
    This is the training signal for future model improvements.
    High-quality interactions (score > 80) are candidates for fine-tuning.
    Low-quality ones (score < 40) should trigger agent config review.
    """
    if not user_id:
        return
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        sb.table('agent_quality_log').upsert({
            'user_id': user_id,
            'agent': agent,
            'message_hash': hash(message[:100]),
            'quality_score': quality_score,
            'issues': issues,
            'logged_at': datetime.now(timezone.utc).isoformat(),
        }, on_conflict='user_id,agent,message_hash').execute()
    except Exception:
        pass  # Table may not exist yet, non-critical
