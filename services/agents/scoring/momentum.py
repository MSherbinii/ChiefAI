"""
Momentum Score engine.
Scores 5 domains 0-100, writes to momentum_scores table.

Body:  based on recovery %, sleep quality trend, workout consistency
Work:  based on commit velocity, comms staleness, deadline proximity
Money: placeholder until Ledger connectors live (defaults to 50)
Admin: based on pending approval queue items, overdue docs
Discipline: cross-domain consistency meta-score
"""
import os
from datetime import datetime, timezone, timedelta
from supabase import create_client

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


def _clamp(val: float, lo: float = 0, hi: float = 100) -> int:
    return int(max(lo, min(hi, val)))


async def calculate_body_score(sb, user_id: str) -> tuple[int, str]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    rec = sb.table('lg_health').select('value').eq('user_id', user_id) \
        .eq('metric', 'recovery').gte('recorded_at', cutoff) \
        .order('recorded_at', desc=True).limit(1).maybe_single().execute()

    sleeps = sb.table('lg_health').select('value').eq('user_id', user_id) \
        .eq('metric', 'sleep').gte('recorded_at', cutoff).execute()

    workouts_7d = sb.table('lg_health').select('id').eq('user_id', user_id) \
        .eq('metric', 'workout').gte('recorded_at', cutoff).execute()

    score = 50.0
    reason_parts = []

    if rec.data:
        recovery = rec.data['value'].get('recovery_score', 50)
        score = 0.5 * recovery
        reason_parts.append(f'recovery {recovery}%')
    else:
        reason_parts.append('no recovery data')

    if sleeps.data:
        avg_quality = sum(s['value'].get('quality', 50) for s in sleeps.data) / len(sleeps.data)
        score += 0.3 * avg_quality
        reason_parts.append(f'sleep quality {avg_quality:.0f}%')
    else:
        score += 15
        reason_parts.append('no sleep data')

    workout_count = len(workouts_7d.data) if workouts_7d.data else 0
    workout_contrib = min(workout_count / 4.0, 1.0) * 20
    score += workout_contrib
    reason_parts.append(f'{workout_count} workouts this week')

    return _clamp(score), ', '.join(reason_parts)


async def calculate_work_score(sb, user_id: str) -> tuple[int, str]:
    cutoff_7d = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    reason_parts = []

    commits = sb.table('lg_health').select('id').eq('user_id', user_id) \
        .eq('metric', 'github_commit').gte('recorded_at', cutoff_7d).execute()
    commit_count = len(commits.data) if commits.data else 0
    commit_contrib = min(commit_count / 10.0, 1.0) * 40
    score = commit_contrib
    reason_parts.append(f'{commit_count} commits this week')

    cutoff_5d = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    stale = sb.table('lg_communications').select('last_message_at') \
        .eq('user_id', user_id).eq('status', 'active') \
        .lte('last_message_at', cutoff_5d).execute()
    stale_count = len(stale.data) if stale.data else 0
    staleness_penalty = min(stale_count * 5, 30)
    score += (60 - staleness_penalty)
    reason_parts.append(f'{stale_count} stale threads (>=5 days)')

    return _clamp(score), ', '.join(reason_parts)


async def calculate_admin_score(sb, user_id: str) -> tuple[int, str]:
    pending = sb.table('approval_queue').select('risk_level') \
        .eq('user_id', user_id).eq('status', 'pending').execute()

    pending_count = len(pending.data) if pending.data else 0
    score = max(0, 100 - pending_count * 10)
    return _clamp(score), f'{pending_count} items pending approval'


async def calculate_momentum(user_id: str) -> dict:
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    body_score, body_reason = await calculate_body_score(sb, user_id)
    work_score, work_reason = await calculate_work_score(sb, user_id)
    admin_score, admin_reason = await calculate_admin_score(sb, user_id)
    money_score = 50
    discipline_score = _clamp((body_score + work_score + admin_score + money_score) / 4)
    total = _clamp((body_score * 0.25 + work_score * 0.3 + money_score * 0.2
                    + admin_score * 0.15 + discipline_score * 0.1))

    scored_at = datetime.now(timezone.utc).isoformat()

    sb.table('momentum_scores').insert({
        'user_id': user_id,
        'total': total,
        'body': body_score,
        'money': money_score,
        'work': work_score,
        'admin': admin_score,
        'discipline': discipline_score,
        'scored_at': scored_at,
    }).execute()

    return {
        'total': total,
        'body': body_score,
        'money': money_score,
        'work': work_score,
        'admin': admin_score,
        'discipline': discipline_score,
        'reasons': {
            'body': body_reason,
            'work': work_reason,
            'admin': admin_reason,
        },
        'scored_at': scored_at,
    }
