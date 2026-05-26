"""
Writes every agent tool call to the audit_trail table.
Called regardless of authority decision outcome.
"""
import os
from datetime import datetime, timezone
from supabase import create_client
from authority.engine import AuthorityResult

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


def log_audit(
    user_id: str,
    result: AuthorityResult,
    executed: bool,
    input_data: dict | None = None,
    output_data: dict | None = None,
    error: str | None = None,
    execution_time_ms: int | None = None,
) -> None:
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        category_map = {
            'log_': 'health', 'read_health': 'health', 'generate_gym': 'health',
            'draft_email': 'communication', 'send_email': 'communication',
            'read_email': 'communication', 'detect_stale': 'communication',
            'read_github': 'projects', 'analyze_commit': 'projects', 'suggest_next': 'projects',
            'read_transaction': 'finance', 'detect_subscription': 'finance',
            'cancel_subscription': 'finance', 'affordability': 'finance',
            'read_document': 'admin', 'extract_document': 'admin', 'draft_reply': 'admin',
        }
        category = 'general'
        for prefix, cat in category_map.items():
            if result.tool_name.startswith(prefix):
                category = cat
                break

        sb.table('audit_trail').insert({
            'user_id': user_id,
            'agent': result.agent,
            'tool_name': result.tool_name,
            'action_category': category,
            'authority_decision': result.decision,
            'executed': executed,
            'execution_time_ms': execution_time_ms,
            'input_data': input_data or {},
            'output_data': output_data or {},
            'error': error,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception:
        pass  # audit logging must never crash the main flow


async def record_approval_outcome(
    user_id: str,
    agent: str,
    tool_name: str,
    approved: bool,
) -> None:
    """Update approval_patterns table — drives auto-approve suggestions."""
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        action_category = tool_name.split('_')[0] if '_' in tool_name else tool_name

        existing = sb.table('approval_patterns') \
            .select('*') \
            .eq('user_id', user_id) \
            .eq('agent', agent) \
            .eq('tool_name', tool_name) \
            .maybe_single().execute()

        if existing.data:
            row = existing.data
            updates = {
                'total_approvals': row['total_approvals'] + (1 if approved else 0),
                'total_denials': row['total_denials'] + (0 if approved else 1),
                'consecutive_approvals': row['consecutive_approvals'] + 1 if approved else 0,
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }
            if updates['consecutive_approvals'] >= 5 and not row.get('auto_approve'):
                updates['auto_approve'] = True
                updates['auto_approve_set_at'] = datetime.now(timezone.utc).isoformat()

            sb.table('approval_patterns').update(updates) \
                .eq('user_id', user_id).eq('agent', agent).eq('tool_name', tool_name).execute()
        else:
            sb.table('approval_patterns').insert({
                'user_id': user_id,
                'agent': agent,
                'action_category': action_category,
                'tool_name': tool_name,
                'consecutive_approvals': 1 if approved else 0,
                'total_approvals': 1 if approved else 0,
                'total_denials': 0 if approved else 1,
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }).execute()
    except Exception:
        pass
