"""
Proactive Intelligence Engine for Chief.
Runs as background tasks, scans Life Graph for anomalies,
generates proactive alerts and queue items BEFORE user asks.

Patterns it detects:
- Health: Recovery declining for 3+ days
- Comms: High-importance thread stale for 5+ days
- Projects: Commit velocity dropped >50% week-over-week
- Finance: Unusual spending spike (when finance data available)
- Admin: Document expiring within 30 days
- Cross-domain: Sleep decline correlating with productivity drop
"""
import os
import asyncio
from datetime import datetime, timezone, timedelta
from supabase import create_client
from pydantic import BaseModel
from typing import Optional
from llm import get_client, AGENT_MODEL

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


class ProactiveAlert(BaseModel):
    user_id: str
    alert_type: str
    agent: str
    title: str
    detail: str
    action: str
    risk_level: str = 'notify'  # auto, notify, approve, confirm
    data: dict = {}
    context_capsule: dict = {}


async def check_health_anomalies(user_id: str) -> list[ProactiveAlert]:
    """Detect health anomalies worth surfacing."""
    alerts = []
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    # Pattern: Recovery declining for 3+ consecutive days
    recoveries = sb.table('lg_health') \
        .select('value, recorded_at') \
        .eq('user_id', user_id) \
        .eq('metric', 'recovery') \
        .gte('recorded_at', cutoff) \
        .order('recorded_at', desc=False) \
        .execute()

    scores = [(r['value'].get('recovery_score', 0), r['recorded_at'])
              for r in (recoveries.data or [])]

    if len(scores) >= 3:
        # Check for 3-day declining trend
        last_3 = scores[-3:]
        if last_3[2][0] < last_3[1][0] < last_3[0][0]:
            drop = last_3[0][0] - last_3[2][0]
            if drop >= 10:
                alerts.append(ProactiveAlert(
                    user_id=user_id,
                    alert_type='recovery_declining',
                    agent='Pulse',
                    title=f'Recovery declining for 3 days (-{drop:.0f}%)',
                    detail=f'Your recovery has dropped from {last_3[0][0]:.0f}% to {last_3[2][0]:.0f}% over the last 3 days.',
                    action='Consider rest day or active recovery',
                    risk_level='notify',
                    data={'drop': drop, 'current': last_3[2][0]},
                    context_capsule={
                        'sources': ['WHOOP recovery data, last 3 days'],
                        'reasoning': f'3 consecutive days of decline from {last_3[0][0]:.0f}% to {last_3[2][0]:.0f}%',
                        'confidence': 'HIGH',
                    }
                ))

    return alerts


async def check_comms_anomalies(user_id: str) -> list[ProactiveAlert]:
    """Detect communication threads that are critically stale."""
    alerts = []
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    cutoff_7d = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    # Pattern: Thread stale 7+ days
    stale = sb.table('lg_communications') \
        .select('subject, participants, channel, last_message_at, staleness_days') \
        .eq('user_id', user_id) \
        .eq('status', 'active') \
        .lte('last_message_at', cutoff_7d) \
        .order('last_message_at', desc=False) \
        .limit(3) \
        .execute()

    for thread in (stale.data or []):
        subj = (thread.get('subject') or '(no subject)')[:60]
        days = thread.get('staleness_days') or 7
        sender = (thread.get('participants') or ['?'])[0][:40]

        alerts.append(ProactiveAlert(
            user_id=user_id,
            alert_type='stale_thread',
            agent='Echo',
            title=f'"{subj[:40]}" — {days} days without reply',
            detail=f'Thread from {sender} via {thread.get("channel", "email")} has been waiting {days} days.',
            action='Draft a reply or mark as resolved',
            risk_level='notify',
            data={'days': days, 'subject': subj, 'sender': sender},
            context_capsule={
                'sources': [f'{thread.get("channel")} thread history'],
                'reasoning': f'No reply in {days} days exceeds normal response time',
                'confidence': 'HIGH',
            }
        ))

    return alerts


async def check_project_anomalies(user_id: str) -> list[ProactiveAlert]:
    """Detect project velocity drops and deadline risks."""
    alerts = []
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # Pattern: Commit velocity dropped >50%
    now = datetime.now(timezone.utc)
    this_week_cutoff = (now - timedelta(days=7)).isoformat()
    last_week_cutoff = (now - timedelta(days=14)).isoformat()

    this_week = sb.table('lg_health') \
        .select('id') \
        .eq('user_id', user_id) \
        .eq('metric', 'github_commit') \
        .gte('recorded_at', this_week_cutoff) \
        .execute()

    last_week = sb.table('lg_health') \
        .select('id') \
        .eq('user_id', user_id) \
        .eq('metric', 'github_commit') \
        .gte('recorded_at', last_week_cutoff) \
        .lt('recorded_at', this_week_cutoff) \
        .execute()

    this_count = len(this_week.data or [])
    last_count = len(last_week.data or [])

    if last_count >= 5 and this_count < last_count * 0.5:
        drop_pct = ((last_count - this_count) / last_count) * 100
        alerts.append(ProactiveAlert(
            user_id=user_id,
            alert_type='velocity_drop',
            agent='Forge',
            title=f'Commit velocity dropped {drop_pct:.0f}% this week',
            detail=f'{this_count} commits this week vs {last_count} last week.',
            action='Check in on project status and remove blockers',
            risk_level='notify',
            data={'this_week': this_count, 'last_week': last_count, 'drop_pct': drop_pct},
            context_capsule={
                'sources': ['GitHub commit history, 2-week comparison'],
                'reasoning': f'{drop_pct:.0f}% velocity drop may indicate blockers or context switching',
                'confidence': 'MEDIUM',
            }
        ))

    # Pattern: Project approaching deadline
    projects = sb.table('lg_projects') \
        .select('name, deadline, type') \
        .eq('user_id', user_id) \
        .eq('status', 'active') \
        .not_.is_('deadline', 'null') \
        .execute()

    for p in (projects.data or []):
        try:
            deadline = datetime.fromisoformat(str(p['deadline']))
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            days_left = (deadline - now).days
            if 0 < days_left <= 14:
                alerts.append(ProactiveAlert(
                    user_id=user_id,
                    alert_type='deadline_approaching',
                    agent='Forge',
                    title=f'{p["name"]} deadline in {days_left} days',
                    detail=f'Project "{p["name"]}" is due on {deadline.strftime("%b %d")}.',
                    action=f'Review {p["name"]} progress and plan remaining work',
                    risk_level='notify' if days_left > 7 else 'approve',
                    data={'project': p['name'], 'days_left': days_left},
                    context_capsule={
                        'sources': ['Project deadline from Life Graph'],
                        'confidence': 'HIGH',
                    }
                ))
        except Exception:
            pass

    return alerts


async def check_cross_domain_patterns(user_id: str) -> list[ProactiveAlert]:
    """
    Detect cross-domain correlations.
    Example: Sleep declining AND commit velocity dropping → likely burned out.
    """
    alerts = []
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    # Get sleep data
    sleeps = sb.table('lg_health') \
        .select('value, recorded_at') \
        .eq('user_id', user_id) \
        .eq('metric', 'sleep') \
        .gte('recorded_at', cutoff) \
        .order('recorded_at', desc=False) \
        .execute()

    # Get commit data
    commits = sb.table('lg_health') \
        .select('id') \
        .eq('user_id', user_id) \
        .eq('metric', 'github_commit') \
        .gte('recorded_at', cutoff) \
        .execute()

    sleep_scores = [s['value'].get('quality', 50) for s in (sleeps.data or [])]
    commit_count = len(commits.data or [])

    if len(sleep_scores) >= 4:
        avg_sleep = sum(sleep_scores) / len(sleep_scores)
        recent_sleep = sum(sleep_scores[-3:]) / 3

        if recent_sleep < 55 and commit_count < 3:
            alerts.append(ProactiveAlert(
                user_id=user_id,
                alert_type='burnout_signal',
                agent='Chief',
                title='Sleep quality + output both declining',
                detail=f'Sleep quality {recent_sleep:.0f}% (below 60%) and only {commit_count} commits this week.',
                action='Consider a recovery day — protect your output by protecting your sleep',
                risk_level='notify',
                data={'avg_sleep': recent_sleep, 'commits': commit_count},
                context_capsule={
                    'sources': ['WHOOP sleep quality, GitHub commit count'],
                    'reasoning': 'Correlated decline in sleep and productivity is a burnout signal',
                    'confidence': 'MEDIUM',
                    'auto_approve_suggested': False,
                }
            ))

    return alerts


async def create_proactive_queue_items(user_id: str, alerts: list[ProactiveAlert]) -> int:
    """
    Write proactive alerts to the approval_queue.
    Only creates items that don't already exist (dedup by alert_type + date).
    Returns count of items created.
    """
    if not alerts:
        return 0

    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    today = datetime.now(timezone.utc).date().isoformat()
    created = 0

    for alert in alerts:
        # Check if we already created this alert type today
        existing = sb.table('approval_queue') \
            .select('id') \
            .eq('user_id', user_id) \
            .eq('action_type', alert.alert_type) \
            .gte('created_at', today) \
            .maybe_single().execute()

        if existing.data:
            continue  # Already alerted today

        sb.table('approval_queue').insert({
            'user_id': user_id,
            'agent': alert.agent,
            'action_type': alert.alert_type,
            'risk_level': alert.risk_level,
            'title': alert.title,
            'description': alert.detail,
            'payload': alert.data,
            'context_capsule': alert.context_capsule,
            'status': 'pending',
        }).execute()
        created += 1

    return created


async def run_proactive_scan(user_id: str) -> dict:
    """
    Run full proactive scan for a user.
    Called by scheduler or manually.
    """
    all_alerts = []

    # Run all scanners
    health_alerts = await check_health_anomalies(user_id)
    comms_alerts = await check_comms_anomalies(user_id)
    project_alerts = await check_project_anomalies(user_id)
    cross_alerts = await check_cross_domain_patterns(user_id)

    all_alerts = health_alerts + comms_alerts + project_alerts + cross_alerts

    created = await create_proactive_queue_items(user_id, all_alerts)

    return {
        'user_id': user_id,
        'alerts_generated': len(all_alerts),
        'queue_items_created': created,
        'alert_types': [a.alert_type for a in all_alerts],
    }


async def run_proactive_scan_all_users() -> dict:
    """Scan all active users. Called by APScheduler every 4 hours."""
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        # Get users who have connected connectors
        users = sb.table('connector_tokens') \
            .select('user_id') \
            .eq('sync_status', 'ok') \
            .execute()

        user_ids = list(set(r['user_id'] for r in (users.data or [])))

        results = []
        for uid in user_ids:
            try:
                result = await run_proactive_scan(uid)
                results.append(result)
            except Exception as e:
                results.append({'user_id': uid, 'error': str(e)})

        return {'scanned': len(user_ids), 'results': results}
    except Exception as e:
        return {'error': str(e)}
