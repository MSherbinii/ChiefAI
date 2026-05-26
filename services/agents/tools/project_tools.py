"""
Real tool implementations for Forge (projects) agent.
Reads GitHub velocity, tracks project health.
"""
import os
import httpx
from datetime import datetime, timezone, timedelta
from supabase import create_client
from pydantic import BaseModel
from typing import Optional

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


class ProjectToolResult(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


async def get_commit_velocity(user_id: str) -> dict:
    """
    Calculate commit velocity: this week vs last week.
    Returns trend, count, and per-repo breakdown.
    """
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        now = datetime.now(timezone.utc)
        week_start = (now - timedelta(days=7)).isoformat()
        two_weeks_start = (now - timedelta(days=14)).isoformat()

        this_week = sb.table('lg_health') \
            .select('value, recorded_at') \
            .eq('user_id', user_id) \
            .eq('metric', 'github_commit') \
            .gte('recorded_at', week_start) \
            .execute()

        last_week = sb.table('lg_health') \
            .select('value, recorded_at') \
            .eq('user_id', user_id) \
            .eq('metric', 'github_commit') \
            .gte('recorded_at', two_weeks_start) \
            .lt('recorded_at', week_start) \
            .execute()

        this_count = len(this_week.data or [])
        last_count = len(last_week.data or [])

        # Per-repo breakdown
        repos_this_week = {}
        for c in (this_week.data or []):
            repo = c['value'].get('repo', 'unknown')
            repos_this_week[repo] = repos_this_week.get(repo, 0) + 1

        # Trend
        if last_count == 0:
            trend = 'no_baseline'
        elif this_count > last_count * 1.2:
            trend = 'improving'
        elif this_count < last_count * 0.8:
            trend = 'declining'
        else:
            trend = 'stable'

        return {
            'this_week': this_count,
            'last_week': last_count,
            'trend': trend,
            'repos': repos_this_week,
            'top_repo': max(repos_this_week, key=repos_this_week.get) if repos_this_week else None,
            'delta': this_count - last_count,
        }
    except Exception as e:
        return {'error': str(e), 'trend': 'error'}


async def get_active_projects(user_id: str) -> list[dict]:
    """Get all active projects with their status."""
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        result = sb.table('lg_projects') \
            .select('name, type, status, deadline, tools, updated_at') \
            .eq('user_id', user_id) \
            .eq('status', 'active') \
            .order('updated_at', desc=True) \
            .limit(10) \
            .execute()

        projects = []
        now = datetime.now(timezone.utc)
        for p in (result.data or []):
            days_until_deadline = None
            if p.get('deadline'):
                try:
                    deadline = datetime.fromisoformat(p['deadline'])
                    if deadline.tzinfo is None:
                        deadline = deadline.replace(tzinfo=timezone.utc)
                    days_until_deadline = (deadline - now).days
                except Exception:
                    pass

            projects.append({
                'name': p['name'],
                'type': p.get('type', 'unknown'),
                'tools': p.get('tools', []),
                'days_until_deadline': days_until_deadline,
                'at_risk': days_until_deadline is not None and days_until_deadline < 14,
            })

        return projects
    except Exception as e:
        return [{'error': str(e)}]


async def flag_stagnant_repos(user_id: str, days_threshold: int = 7) -> list[dict]:
    """Find repos with no commits in N days that should have activity."""
    try:
        velocity = await get_commit_velocity(user_id)
        active_repos = set(velocity.get('repos', {}).keys())

        projects = await get_active_projects(user_id)
        github_projects = [p for p in projects if 'github' in (p.get('tools') or [])]

        stagnant = []
        for p in github_projects:
            if p['name'] not in active_repos:
                stagnant.append({
                    'repo': p['name'],
                    'days_since_commit': f'>{days_threshold}',
                    'at_risk': p.get('at_risk', False),
                })

        return stagnant
    except Exception as e:
        return [{'error': str(e)}]
