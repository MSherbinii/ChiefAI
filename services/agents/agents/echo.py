# services/agents/agents/echo.py
"""
Echo v2 — Case-Aware Communication Agent.

Upgrade from "summarize recent threads" to "situation navigator".
Now queries email_cases first to provide timeline-based answers.

Examples:
  "What's happening with Deutsche Bank?" → finds stalled account case → full timeline
  "What emails need attention?" → lists active cases by priority
  "Write a follow-up to Congstar" → finds billing case → drafts with full context
"""
import os
from datetime import datetime, timezone, timedelta
from supabase import create_client
from agents.base import BaseAgent
from models import ChatRequest, ChatResponse
from llm import get_client, BRIEF_MODEL
from tools.comms_tools import get_stale_threads, create_draft_in_queue
from db import safe_single

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

# Keywords that suggest the user is asking about a specific situation/case
CASE_QUERY_KEYWORDS = [
    "what's happening", "what happened", "what's going on",
    "status of", "update on", "situation with",
    "deutsche bank", "fitstar", "mcfit", "congstar", "immoscout",
    "debt collector", "inkasso", "mahnung", "forderung",
    "my account", "my application", "my apartment",
    "follow up", "follow-up", "did they reply", "still waiting",
    "stalled", "no response", "haven't heard",
]


async def _fetch_cases_context(user_id: str, query: str) -> str:
    """
    Query email_cases for relevant cases based on user's message.
    Applies smart filtering: active/recent cases, relevance scoring.
    """
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    now = datetime.now(timezone.utc)
    cutoff_active = (now - timedelta(days=365)).isoformat()  # Only show cases from last year by default

    # Get active non-resolved cases
    cases = sb.table('email_cases').select(
        'id, title, status, priority, category, summary, pending_action, stalled_since, timeline, entities, confidence, updated_at'
    ).eq('user_id', user_id) \
     .neq('status', 'resolved') \
     .order('priority', desc=True) \
     .limit(30).execute()

    if not cases.data:
        # If no active cases, check for any recent high-priority ones
        cases = sb.table('email_cases').select(
            'id, title, status, priority, summary, pending_action'
        ).eq('user_id', user_id).in_('priority', ['critical', 'high']).limit(10).execute()
        if not cases.data:
            return ''

    PRIORITY_EMOJI = {'critical': 'CRITICAL', 'high': 'HIGH', 'normal': 'NORMAL', 'low': 'LOW'}
    STATUS_LABEL = {
        'open': 'Open', 'progressing': 'In Progress',
        'stalled': 'STALLED', 'needs_action': 'ACTION NEEDED', 'resolved': 'Resolved'
    }

    lines = ['=== ACTIVE CASES (from email analysis) ===']

    # Score relevance against query
    query_lower = query.lower()
    query_words = [w for w in query_lower.split() if len(w) > 3]

    scored_cases = []
    for case in cases.data:
        title_lower = (case.get('title') or '').lower()
        summary_lower = (case.get('summary') or '').lower()

        # Relevance score
        relevance = sum(1 for w in query_words if w in title_lower or w in summary_lower)

        # Priority weight
        priority_weight = {'critical': 4, 'high': 3, 'normal': 2, 'low': 1}.get(case.get('priority', 'normal'), 2)

        # Status weight (needs_action > stalled > progressing > open)
        status_weight = {'needs_action': 3, 'stalled': 2, 'progressing': 2, 'open': 1}.get(case.get('status', 'open'), 1)

        scored_cases.append((relevance * 10 + priority_weight + status_weight, case))

    scored_cases.sort(key=lambda x: x[0], reverse=True)
    display_cases = [c for _, c in scored_cases[:7]]  # Show top 7

    for case in display_cases:
        priority = PRIORITY_EMOJI.get(case.get('priority', 'normal'), 'NORMAL')
        status = STATUS_LABEL.get(case.get('status', 'open'), 'Open')
        title = case.get('title', 'Unnamed case')
        summary = case.get('summary', '')
        pending = case.get('pending_action')
        stalled = case.get('stalled_since')

        lines.append(f'\n[{priority}] Case: {title}')
        lines.append(f'   Status: {status}')
        if summary:
            lines.append(f'   {summary[:180]}')
        if pending:
            lines.append(f'   -> Action needed: {pending}')
        if stalled:
            try:
                stalled_dt = datetime.fromisoformat(stalled.replace('Z', '+00:00'))
                days_stalled = (now - stalled_dt).days
                lines.append(f'   STALLED for {days_stalled} days')
            except Exception:
                pass

        # Include timeline for specific queries
        if query_words and any(w in (case.get('title', '') + case.get('summary', '')).lower() for w in query_words):
            timeline = case.get('timeline', []) or []
            if timeline:
                lines.append('   Timeline:')
                for event in timeline[-5:]:
                    d = event.get('date', '')[:10]
                    ev = event.get('event', '')[:100]
                    direction = '->' if event.get('direction') == 'sent' else '<-'
                    lines.append(f'     {d} {direction} {ev}')

    if not display_cases:
        lines.append('No active cases found.')

    lines.append('\nIMPORTANT: These are REAL cases from email analysis. Reference them directly in your answer.')
    return '\n'.join(lines)


async def _fetch_raw_email_context(user_id: str) -> str:
    """Fallback: recent email threads from lg_communications (Phase 0 data)."""
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    cutoff_3d = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    cutoff_2d = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()

    stale = sb.table('lg_communications').select(
        'thread_id, channel, participants, subject, last_message_at, staleness_days'
    ).eq('user_id', user_id).eq('status', 'active') \
     .lte('last_message_at', cutoff_3d) \
     .order('last_message_at', desc=False).limit(10).execute()

    for t in stale.data or []:
        if t.get('last_message_at'):
            try:
                lma = datetime.fromisoformat(t['last_message_at'].replace('Z', '+00:00'))
                t['staleness_days'] = (datetime.now(timezone.utc) - lma).days
            except Exception:
                pass

    recent = sb.table('lg_communications').select(
        'subject, channel, participants, last_message_at'
    ).eq('user_id', user_id).eq('status', 'active') \
     .gte('last_message_at', cutoff_2d) \
     .order('last_message_at', desc=True).limit(5).execute()

    lines = ['=== RECENT EMAILS ===']

    if stale.data:
        lines.append(f'Threads needing attention ({len(stale.data)}):')
        for t in stale.data:
            subj = (t.get('subject') or '(no subject)')[:60]
            sender = (t.get('participants') or ['?'])[0][:40]
            lines.append(f'  [{t.get("staleness_days", "?")}d] "{subj}" from {sender}')

    if recent.data:
        lines.append(f'Recent emails ({len(recent.data)}):')
        for t in recent.data:
            subj = (t.get('subject') or '(no subject)')[:60]
            lines.append(f'  "{subj}" — {t.get("last_message_at", "")[:10]}')

    if not stale.data and not recent.data:
        lines.append('No recent email threads found.')

    lines.append('\nIMPORTANT: This is real email data from Gmail. Use it to answer.')
    return '\n'.join(lines)


class EchoAgent(BaseAgent):
    name = 'Echo'
    description = 'Communication: emails, cases, situation tracking, drafting replies, follow-ups.'

    async def fetch_context(self, user_id: str) -> str:
        """Case-aware context: try Cases first, fall back to raw threads."""
        if not user_id:
            return 'No user context available.'

        # Always include cases if they exist
        cases_ctx = await _fetch_cases_context(user_id, '')
        raw_ctx = await _fetch_raw_email_context(user_id)

        parts = []
        if cases_ctx:
            parts.append(cases_ctx)
        if raw_ctx and 'No recent' not in raw_ctx:
            parts.append(raw_ctx)

        return '\n\n'.join(parts) if parts else 'No email data available yet.'

    async def handle(self, request: ChatRequest) -> ChatResponse:
        msg_lower = request.message.lower()
        user_id = request.user_id or ''

        # Determine if this is a case-specific query
        is_case_query = any(kw in msg_lower for kw in CASE_QUERY_KEYWORDS)

        # Build context — case-aware for relevant queries, full context otherwise
        if is_case_query and user_id:
            cases_ctx = await _fetch_cases_context(user_id, request.message)
            raw_ctx = await _fetch_raw_email_context(user_id)
            context = cases_ctx + ('\n\n' + raw_ctx if raw_ctx else '')
        else:
            context = await self.build_full_context(user_id, request.message)

        client = get_client()
        messages = [{'role': m.role, 'content': m.content} for m in request.history]

        # Inject context as assistant message (Sonnet handles this better than system prompt)
        if context:
            messages.append({
                'role': 'assistant',
                'content': f'[Loading email context...]\n\n{context}\n\n[Context loaded. Answering based on real data.]'
            })

        messages.append({'role': 'user', 'content': request.message})

        response = client.messages.create(
            model=BRIEF_MODEL,  # Sonnet — Haiku over-refuses email data
            max_tokens=1024,
            system=self.system_prompt,
            messages=messages,
        )
        return ChatResponse(reply=response.content[0].text, agent='Echo')
