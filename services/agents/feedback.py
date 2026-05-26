"""
Reinforcement learning feedback loop for Chief agents.
User approvals/rejections are the training signal.
This module:
1. Records outcome of each approval/rejection
2. Updates approval_patterns for auto-approve learning
3. Generates quality signal for agent behavior improvement
4. Identifies which agent behaviors to reinforce vs discourage
"""
import os
from datetime import datetime, timezone, timedelta
from supabase import create_client
from pydantic import BaseModel
from typing import Optional

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


class ApprovalOutcome(BaseModel):
    queue_item_id: str
    user_id: str
    approved: bool
    time_to_decision_seconds: Optional[float] = None


class AgentPerformanceReport(BaseModel):
    agent: str
    total_actions: int
    approval_rate: float  # 0-1
    auto_approve_count: int
    avg_time_to_decision: Optional[float]
    improvement_areas: list[str]
    reinforced_behaviors: list[str]


async def record_approval_feedback(outcome: ApprovalOutcome) -> dict:
    """
    Record approval/rejection feedback and update learning state.
    This is the core RL training signal.
    """
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # Get the queue item details
    item = sb.table('approval_queue') \
        .select('agent, action_type, title, payload, context_capsule') \
        .eq('id', outcome.queue_item_id) \
        .eq('user_id', outcome.user_id) \
        .maybe_single().execute()

    if not item.data:
        return {'error': 'Queue item not found'}

    agent = item.data.get('agent', 'Chief')
    action_type = item.data.get('action_type', 'unknown')
    action_category = action_type.split('_')[0] if '_' in action_type else action_type

    # Update approval_patterns (the learning table)
    existing = sb.table('approval_patterns') \
        .select('*') \
        .eq('user_id', outcome.user_id) \
        .eq('agent', agent) \
        .eq('tool_name', action_type) \
        .maybe_single().execute()

    if existing.data:
        row = existing.data
        new_consecutive = (row['consecutive_approvals'] + 1) if outcome.approved else 0
        updates = {
            'total_approvals': row['total_approvals'] + (1 if outcome.approved else 0),
            'total_denials': row['total_denials'] + (0 if outcome.approved else 1),
            'consecutive_approvals': new_consecutive,
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }
        # Auto-approve after 5 consecutive approvals
        if new_consecutive >= 5 and not row.get('auto_approve'):
            updates['auto_approve'] = True
            updates['auto_approve_set_at'] = datetime.now(timezone.utc).isoformat()
        # Revoke auto-approve after a rejection
        if not outcome.approved and row.get('auto_approve'):
            updates['auto_approve'] = False
            updates['consecutive_approvals'] = 0

        sb.table('approval_patterns').update(updates) \
            .eq('user_id', outcome.user_id) \
            .eq('agent', agent) \
            .eq('tool_name', action_type) \
            .execute()
    else:
        sb.table('approval_patterns').insert({
            'user_id': outcome.user_id,
            'agent': agent,
            'action_category': action_category,
            'tool_name': action_type,
            'consecutive_approvals': 1 if outcome.approved else 0,
            'total_approvals': 1 if outcome.approved else 0,
            'total_denials': 0 if outcome.approved else 1,
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }).execute()

    # Log to audit trail
    sb.table('audit_trail').insert({
        'user_id': outcome.user_id,
        'agent': agent,
        'tool_name': action_type,
        'action_category': action_category,
        'authority_decision': 'approved' if outcome.approved else 'denied',
        'executed': outcome.approved,
        'input_data': {'queue_item_id': outcome.queue_item_id},
        'output_data': {'time_to_decision': outcome.time_to_decision_seconds},
        'created_at': datetime.now(timezone.utc).isoformat(),
    }).execute()

    return {
        'agent': agent,
        'action_type': action_type,
        'approved': outcome.approved,
        'consecutive_approvals': (existing.data['consecutive_approvals'] + 1) if existing.data and outcome.approved else (1 if outcome.approved else 0),
        'auto_approve_enabled': False,  # Will be true after 5 consecutive
    }


async def get_agent_performance(user_id: str, agent: str, days: int = 30) -> AgentPerformanceReport:
    """
    Generate a performance report for an agent over the last N days.
    This drives model behavior reinforcement decisions.
    """
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # Get audit trail for this agent
    audit = sb.table('audit_trail') \
        .select('authority_decision, executed, execution_time_ms, tool_name') \
        .eq('user_id', user_id) \
        .eq('agent', agent) \
        .gte('created_at', cutoff) \
        .execute()

    rows = audit.data or []
    total = len(rows)
    if total == 0:
        return AgentPerformanceReport(
            agent=agent, total_actions=0, approval_rate=0,
            auto_approve_count=0, avg_time_to_decision=None,
            improvement_areas=['No data yet'], reinforced_behaviors=[]
        )

    approved = sum(1 for r in rows if r['authority_decision'] == 'approved')
    approval_rate = approved / total if total > 0 else 0

    auto_approved = sb.table('approval_patterns') \
        .select('tool_name') \
        .eq('user_id', user_id) \
        .eq('agent', agent) \
        .eq('auto_approve', True) \
        .execute()

    # Derive improvement areas from patterns
    denied_tools = [r['tool_name'] for r in rows if r['authority_decision'] == 'denied']
    denied_counts: dict[str, int] = {}
    for t in denied_tools:
        denied_counts[t] = denied_counts.get(t, 0) + 1

    improvement_areas = [f'Reduce {t} actions (denied {c}x)' for t, c in denied_counts.items() if c >= 2]
    reinforced = [r['tool_name'] for r in (auto_approved.data or [])]

    return AgentPerformanceReport(
        agent=agent,
        total_actions=total,
        approval_rate=round(approval_rate, 2),
        auto_approve_count=len(auto_approved.data or []),
        avg_time_to_decision=None,
        improvement_areas=improvement_areas or ['Performance looks good'],
        reinforced_behaviors=reinforced,
    )


async def should_auto_approve(user_id: str, agent: str, action_type: str) -> bool:
    """
    Check if a specific action type should be auto-approved.
    Used by orchestrator before creating approval_queue items.
    """
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        result = sb.table('approval_patterns') \
            .select('auto_approve') \
            .eq('user_id', user_id) \
            .eq('agent', agent) \
            .eq('tool_name', action_type) \
            .maybe_single().execute()

        return bool(result.data and result.data.get('auto_approve'))
    except Exception:
        return False
