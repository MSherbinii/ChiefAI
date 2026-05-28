from dotenv import load_dotenv
load_dotenv()  # must be before all imports that read env vars

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from models import ChatRequest, ChatResponse
from orchestrator import route_and_handle
from voice_intent import classify_voice_intent, VoiceIntent
from scoring.momentum import calculate_momentum
from brief.generator import generate_morning_brief
from connectors.gmail import sync_gmail
from connectors.github import sync_github
from connectors.whoop import sync_whoop
from connectors.imap_email import sync_imap
from connectors.google_calendar import sync_google_calendar
from feedback import record_approval_feedback, get_agent_performance, ApprovalOutcome
from embeddings import update_entity_embeddings, update_communication_embeddings
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from proactive import run_proactive_scan_all_users, run_proactive_scan
from knowledge_extractor import run_background_extraction
from hierarchy import get_pending_tasks, delegate_task, AGENT_HIERARCHY
from document_extractor import extract_document_fields, DocumentExtractRequest, ExtractedDocument
from email_intelligence import deep_scan_inbox, get_scan_status, cluster_entities, detect_subscriptions
from email_intelligence.case_discoverer import run_case_discovery, apply_lifecycle_rules
from email_intelligence.cross_entity_reasoner import run_cross_entity_reasoning, merge_linked_cases
from email_intelligence.pattern_scanner import create_cases_from_patterns, scan_for_patterns
from supabase import create_client
from datetime import datetime, timezone
import asyncio

scheduler = AsyncIOScheduler()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


async def run_daily_brief_for_all():
    """Run morning brief + momentum score for all connected users."""
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        users = sb.table('connector_tokens') \
            .select('user_id') \
            .eq('sync_status', 'ok') \
            .execute()
        user_ids = list(set(r['user_id'] for r in (users.data or [])))

        for uid in user_ids:
            try:
                await calculate_momentum(uid)
                await generate_morning_brief(uid)
            except Exception as e:
                print(f'Brief generation failed for {uid}: {e}')
    except Exception as e:
        print(f'Daily brief job error: {e}')


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(
        run_proactive_scan_all_users,
        'interval',
        hours=4,
        id='proactive_scan',
        replace_existing=True,
    )
    scheduler.add_job(
        run_daily_brief_for_all,
        'cron',
        hour=7, minute=0,
        id='daily_brief',
        replace_existing=True,
    )
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title='Chief Agent Service', version='0.1.0', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


class SyncRequest(BaseModel):
    user_id: str


class BriefRequest(BaseModel):
    user_id: str
    user_name: str = 'there'


class EmailScanRequest(BaseModel):
    user_id: str


class IMAPVerifyRequest(BaseModel):
    email: str
    password: str
    imap_host: str
    imap_port: int = 993


class EmailFeedbackRequest(BaseModel):
    user_id: str
    feedback_type: str  # case_confirm, case_reject, case_merge, entity_correct, context_injection
    target_id: Optional[str] = None
    target_type: Optional[str] = None  # case, entity, subscription
    old_value: Optional[dict] = None
    new_value: Optional[dict] = None
    context: Optional[str] = None


class CaseNoteRequest(BaseModel):
    user_id: str
    note: str


class MergeCasesRequest(BaseModel):
    user_id: str
    case_id_1: str
    case_id_2: str
    reason: str


class UnsubscribeRequest(BaseModel):
    user_id: str
    subscription_id: str


@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'chief-agents'}


@app.post('/chat', response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    return await route_and_handle(request)


class VoiceClassifyRequest(BaseModel):
    transcript: str
    context: str = ''


@app.post('/voice/classify', response_model=VoiceIntent)
async def classify_voice(req: VoiceClassifyRequest) -> VoiceIntent:
    return classify_voice_intent(req.transcript, req.context)


@app.post('/sync/google')
async def sync_google(req: SyncRequest):
    asyncio.create_task(sync_gmail(req.user_id))
    return {'status': 'sync_started', 'connector': 'gmail'}


@app.post('/sync/github')
async def sync_github_route(req: SyncRequest):
    asyncio.create_task(sync_github(req.user_id))
    return {'status': 'sync_started', 'connector': 'github'}


@app.post('/sync/whoop')
async def sync_whoop_route(req: SyncRequest):
    asyncio.create_task(sync_whoop(req.user_id))
    return {'status': 'sync_started', 'connector': 'whoop'}


@app.post('/sync/imap_uni')
async def sync_imap_route(req: SyncRequest):
    asyncio.create_task(sync_imap(req.user_id))
    return {'status': 'sync_started', 'connector': 'imap_uni'}


@app.post('/sync/google_calendar')
async def sync_calendar(req: SyncRequest):
    asyncio.create_task(sync_google_calendar(req.user_id))
    return {'status': 'sync_started', 'connector': 'google_calendar'}


@app.post('/email/deep-scan')
async def start_deep_scan(req: EmailScanRequest):
    """Trigger full inbox deep scan + entity clustering + subscription detection."""
    async def pipeline():
        try:
            await deep_scan_inbox(req.user_id)
            await cluster_entities(req.user_id)
            await detect_subscriptions(req.user_id)
        except Exception as e:
            from supabase import create_client
            import os as _os
            sb = create_client(
                _os.getenv('SUPABASE_URL'),
                _os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            )
            try:
                sb.table('email_scan_status').update({
                    'status': 'error',
                    'error_message': str(e)[:200],
                }).eq('user_id', req.user_id).execute()
            except Exception:
                pass

    asyncio.create_task(pipeline())
    return {'status': 'scan_started', 'user_id': req.user_id}


@app.get('/email/scan-status/{user_id}')
async def email_scan_status(user_id: str):
    """Get current deep scan progress."""
    return await get_scan_status(user_id)


@app.get('/email/subscriptions/{user_id}')
async def list_email_subscriptions(user_id: str):
    """List detected email subscriptions for a user."""
    from supabase import create_client
    import os as _os
    sb = create_client(_os.getenv('SUPABASE_URL'), _os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
    res = sb.table('email_subscriptions').select('*') \
        .eq('user_id', user_id) \
        .eq('status', 'active') \
        .order('engagement_score', desc=False) \
        .limit(100).execute()
    return {'subscriptions': res.data or [], 'total': len(res.data or [])}


@app.get('/email/stats/{user_id}')
async def email_stats(user_id: str):
    """Get email intelligence statistics for a user."""
    from supabase import create_client
    import os as _os
    sb = create_client(_os.getenv('SUPABASE_URL'), _os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

    raw_res = sb.table('email_raw').select('id', count='exact').eq('user_id', user_id).limit(1).execute()
    sub_res = sb.table('email_subscriptions').select('id', count='exact').eq('user_id', user_id).eq('status', 'active').limit(1).execute()
    entity_res = sb.table('entities').select('id', count='exact').eq('user_id', user_id).not_.is_('relationship_type', 'null').limit(1).execute()
    scan = await get_scan_status(user_id)

    return {
        'total_emails': raw_res.count or 0,
        'subscriptions': sub_res.count or 0,
        'entities': entity_res.count or 0,
        'scan_status': scan.get('status', 'idle'),
    }


def _build_interview_message(cases: list, dead_subs: list) -> str:
    """Build the natural-language initial interview message."""
    lines = ["I've analyzed your full inbox. Here's what I found:\n"]

    PRIORITY_EMOJI = {'critical': '🔴', 'high': '🟠', 'normal': '🟡', 'low': '🟢'}
    for i, c in enumerate(cases[:6], 1):
        emoji = PRIORITY_EMOJI.get(c.get('priority', 'normal'), '🟡')
        status = c.get('status', 'open').replace('_', ' ').title()
        title = c.get('title', 'Unknown')
        summary = c.get('summary', '')[:100] if c.get('summary') else ''
        pending = c.get('pending_action', '')
        lines.append(f'{i}. {emoji} {title} ({status})')
        if summary:
            lines.append(f'   {summary}')
        if pending:
            lines.append(f'   → Next: {pending}')

    if dead_subs:
        lines.append(f'\nAlso found {len(dead_subs)} newsletters you never open — want me to clean those up?')

    lines.append('\nDid I get these right? Anything missing or wrong?')
    return '\n'.join(lines)


@app.post('/email/cases/run-discovery')
async def run_email_case_discovery(req: EmailScanRequest):
    """Trigger case discovery pipeline: discover_cases → cross_entity_reasoning."""
    async def pipeline():
        try:
            await run_case_discovery(req.user_id)
            await run_cross_entity_reasoning(req.user_id)
        except Exception as e:
            pass  # Cases are best-effort

    asyncio.create_task(pipeline())
    return {'status': 'discovery_started', 'user_id': req.user_id}


@app.get('/email/cases/{user_id}')
async def list_email_cases(user_id: str, status: Optional[str] = None):
    """List all active email cases for a user."""
    from supabase import create_client
    import os as _os
    sb = create_client(_os.getenv('SUPABASE_URL'), _os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

    query = sb.table('email_cases').select(
        'id, title, status, priority, category, summary, pending_action, stalled_since, confidence, updated_at'
    ).eq('user_id', user_id)

    if status:
        query = query.eq('status', status)
    else:
        query = query.neq('status', 'resolved')

    result = query.order('priority', desc=True).limit(50).execute()
    return {'cases': result.data or [], 'total': len(result.data or [])}


@app.get('/email/case/{case_id}')
async def get_email_case(case_id: str):
    """Get full case details including timeline."""
    from supabase import create_client
    import os as _os
    sb = create_client(_os.getenv('SUPABASE_URL'), _os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
    result = sb.table('email_cases').select('*').eq('id', case_id).maybe_single().execute()
    if not result.data:
        return {'error': 'Case not found'}, 404
    return result.data


@app.post('/email/case/{case_id}/resolve')
async def resolve_case(case_id: str, req: CaseNoteRequest):
    """User marks a case as resolved (with optional reason). Stores RL feedback."""
    from supabase import create_client
    import os as _os
    sb = create_client(_os.getenv('SUPABASE_URL'), _os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

    sb.table('email_cases').update({
        'status': 'resolved',
        'user_notes': req.note or 'Resolved by user',
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }).eq('id', case_id).eq('user_id', req.user_id).execute()

    sb.table('email_feedback').insert({
        'user_id': req.user_id,
        'feedback_type': 'case_reject',
        'target_id': case_id,
        'target_type': 'case',
        'old_value': {'status': 'open'},
        'new_value': {'status': 'resolved', 'reason': req.note},
        'created_at': datetime.now(timezone.utc).isoformat(),
    }).execute()

    return {'ok': True, 'case_id': case_id, 'status': 'resolved'}


@app.post('/email/case/{case_id}/note')
async def add_case_note(case_id: str, req: CaseNoteRequest):
    """Add user context/note to a case (RL signal: context_injection)."""
    from supabase import create_client
    import os as _os
    sb = create_client(_os.getenv('SUPABASE_URL'), _os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

    # Update user_notes on the case
    sb.table('email_cases').update({
        'user_notes': req.note,
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }).eq('id', case_id).execute()

    # Store as RL feedback
    sb.table('email_feedback').insert({
        'user_id': req.user_id,
        'feedback_type': 'context_injection',
        'target_id': case_id,
        'target_type': 'case',
        'new_value': {'note': req.note},
        'created_at': datetime.now(timezone.utc).isoformat(),
    }).execute()

    return {'ok': True, 'case_id': case_id}


@app.post('/email/feedback')
async def email_feedback(req: EmailFeedbackRequest):
    """Store RL feedback signal from user corrections."""
    from supabase import create_client
    import os as _os
    sb = create_client(_os.getenv('SUPABASE_URL'), _os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

    sb.table('email_feedback').insert({
        'user_id': req.user_id,
        'feedback_type': req.feedback_type,
        'target_id': req.target_id,
        'target_type': req.target_type,
        'old_value': req.old_value,
        'new_value': req.new_value,
        'context': req.context,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }).execute()

    # Apply feedback immediately for entity corrections
    if req.feedback_type == 'entity_correct' and req.target_id and req.new_value:
        new_rtype = req.new_value.get('relationship_type')
        if new_rtype:
            sb.table('entities').update({'relationship_type': new_rtype}) \
                .eq('id', req.target_id).execute()

    # Apply case status changes
    if req.feedback_type in ('case_confirm', 'case_reject') and req.target_id:
        if req.feedback_type == 'case_reject':
            sb.table('email_cases').update({'status': 'resolved', 'confidence': 0.1}) \
                .eq('id', req.target_id).execute()

    return {'ok': True}


@app.post('/email/cases/merge')
async def merge_email_cases(req: MergeCasesRequest):
    """Merge two cases that the user identifies as the same situation."""
    master_id = await merge_linked_cases(
        req.user_id, req.case_id_1, req.case_id_2, req.reason
    )

    # Store feedback
    from supabase import create_client
    import os as _os
    sb = create_client(_os.getenv('SUPABASE_URL'), _os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
    sb.table('email_feedback').insert({
        'user_id': req.user_id,
        'feedback_type': 'case_merge',
        'target_id': master_id,
        'target_type': 'case',
        'new_value': {'merged_from': req.case_id_2, 'reason': req.reason},
        'created_at': datetime.now(timezone.utc).isoformat(),
    }).execute()

    return {'ok': True, 'master_case_id': master_id}


@app.post('/email/pattern-scan')
async def run_pattern_scan(req: EmailScanRequest):
    """Pattern-first case discovery: scan all emails for dispute/billing/legal patterns."""
    asyncio.create_task(create_cases_from_patterns(req.user_id))
    return {'status': 'pattern_scan_started', 'user_id': req.user_id}


@app.post('/email/lifecycle')
async def run_lifecycle(req: EmailScanRequest):
    """Apply lifecycle rules: archive old cases, demote stale ones."""
    result = await apply_lifecycle_rules(req.user_id)
    return result


@app.get('/email/pattern-groups/{user_id}')
async def get_pattern_groups(user_id: str):
    """Preview which email groups triggered pattern detection."""
    groups = await scan_for_patterns(user_id)
    return {
        'groups': [
            {
                'domain': g['domain'],
                'email_count': g['email_count'],
                'importance': g['total_importance'],
                'category': g['primary_category'],
                'sample': g['sample_emails'][0]['subject'][:60] if g['sample_emails'] else '',
            }
            for g in groups[:20]
        ],
        'total': len(groups),
    }


@app.post('/email/unsubscribe')
async def queue_unsubscribe(req: UnsubscribeRequest):
    """Queue an unsubscribe action for a detected subscription."""
    from supabase import create_client
    import os as _os
    sb = create_client(_os.getenv('SUPABASE_URL'), _os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

    # Get subscription details
    sub = sb.table('email_subscriptions').select('*').eq('id', req.subscription_id) \
        .eq('user_id', req.user_id).maybe_single().execute()

    if not sub.data:
        return {'error': 'Subscription not found'}

    # Create approval queue item
    sb.table('approval_queue').insert({
        'user_id': req.user_id,
        'agent': 'Clerk',
        'action_type': 'unsubscribe_email',
        'risk_level': 'approve',
        'title': f'Unsubscribe from {sub.data.get("sender_name") or sub.data["sender_email"]}',
        'description': f'Remove from mailing list: {sub.data["sender_email"]}. Total received: {sub.data.get("total_received", 0)} emails.',
        'payload': {
            'sender_email': sub.data['sender_email'],
            'unsubscribe_url': sub.data.get('unsubscribe_url'),
            'subscription_id': req.subscription_id,
        },
        'context_capsule': {
            'sources': ['email_subscriptions table'],
            'reasoning': f'Engagement score: {sub.data.get("engagement_score", 0):.0%}, last received: {sub.data.get("last_received", "unknown")[:10]}',
            'confidence': 'HIGH',
        },
        'status': 'pending',
        'created_at': datetime.now(timezone.utc).isoformat(),
    }).execute()

    # Mark subscription as decision pending
    sb.table('email_subscriptions').update({'user_decision': 'unsubscribe'}) \
        .eq('id', req.subscription_id).execute()

    return {'ok': True, 'queued': True, 'sender': sub.data['sender_email']}


@app.get('/email/present-cases/{user_id}')
async def present_cases_summary(user_id: str):
    """
    Return a structured summary of cases for Echo to present to the user.
    Used after case discovery to initiate the initial interview.
    """
    from supabase import create_client
    import os as _os
    sb = create_client(_os.getenv('SUPABASE_URL'), _os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

    cases = sb.table('email_cases').select(
        'id, title, status, priority, category, summary, pending_action'
    ).eq('user_id', user_id).neq('status', 'resolved') \
     .order('priority', desc=True).limit(10).execute()

    subs = sb.table('email_subscriptions').select('id, sender_email, total_received, engagement_score') \
        .eq('user_id', user_id).eq('status', 'active') \
        .lt('engagement_score', 0.2).execute()

    return {
        'cases': cases.data or [],
        'dead_subscriptions': subs.data or [],
        'message': _build_interview_message(cases.data or [], subs.data or []),
    }


@app.post('/score/momentum')
async def score_momentum(req: SyncRequest):
    result = await calculate_momentum(req.user_id)
    return result


@app.post('/brief/generate')
async def generate_brief(req: BriefRequest):
    result = await generate_morning_brief(req.user_id, req.user_name)
    return result


class FeedbackRequest(BaseModel):
    queue_item_id: str
    user_id: str
    approved: bool
    time_to_decision_seconds: Optional[float] = None


@app.post('/feedback/approval')
async def approval_feedback(req: FeedbackRequest):
    result = await record_approval_feedback(ApprovalOutcome(
        queue_item_id=req.queue_item_id,
        user_id=req.user_id,
        approved=req.approved,
        time_to_decision_seconds=req.time_to_decision_seconds,
    ))
    return result


@app.get('/feedback/performance/{user_id}/{agent}')
async def agent_performance(user_id: str, agent: str):
    return await get_agent_performance(user_id, agent)


@app.post('/embeddings/update')
async def update_embeddings(req: SyncRequest):
    entities = await update_entity_embeddings(req.user_id)
    comms = await update_communication_embeddings(req.user_id)
    return {'entities': entities, 'communications': comms}


@app.post('/proactive/scan')
async def proactive_scan(req: SyncRequest):
    result = await run_proactive_scan(req.user_id)
    return result


@app.post('/knowledge/extract')
async def extract_knowledge(req: SyncRequest):
    asyncio.create_task(run_background_extraction(req.user_id))
    return {'status': 'extraction_started'}


@app.post('/connectors/imap/verify')
async def verify_imap_route(req: IMAPVerifyRequest):
    import imaplib
    try:
        mail = imaplib.IMAP4_SSL(req.imap_host, req.imap_port)
        mail.login(req.email, req.password)
        mail.logout()
        return {'ok': True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'IMAP connection failed: {str(e)}')


# ---------------------------------------------------------------------------
# Hierarchy endpoints — agent tree, pending tasks, delegation
# ---------------------------------------------------------------------------

@app.get('/hierarchy')
async def get_hierarchy():
    return {name: node.dict() for name, node in AGENT_HIERARCHY.items()}


@app.get('/hierarchy/tasks/{user_id}/{agent}')
async def agent_tasks(user_id: str, agent: str):
    return {'tasks': await get_pending_tasks(user_id, agent)}


class DelegateRequest(BaseModel):
    user_id: str
    from_agent: str = 'Chief'
    to_agent: str
    task: str
    why: Optional[str] = None
    priority: str = 'normal'


@app.post('/documents/extract', response_model=ExtractedDocument)
async def extract_document(req: DocumentExtractRequest) -> ExtractedDocument:
    return await extract_document_fields(req)


@app.post('/hierarchy/delegate')
async def delegate(req: DelegateRequest):
    return await delegate_task(
        user_id=req.user_id,
        from_agent=req.from_agent,
        to_agent=req.to_agent,
        task=req.task,
        why=req.why,
        priority=req.priority,
    )


# ---------------------------------------------------------------------------
# Eval endpoint — run agent evaluation suite
# ---------------------------------------------------------------------------

@app.post('/eval/run')
async def run_eval():
    """Run all agent evaluations. Returns quality report."""
    from eval.runner import run_all_evaluations
    results = await run_all_evaluations()
    return results
