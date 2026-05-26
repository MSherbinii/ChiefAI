import os
from datetime import datetime, timezone, timedelta
from supabase import create_client
from agents.base import BaseAgent
from models import ChatRequest, ChatResponse
from llm import get_client, AGENT_MODEL
from tools.project_tools import get_commit_velocity, get_active_projects, flag_stagnant_repos

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


class ForgeAgent(BaseAgent):
    name = 'Forge'
    description = 'Projects: thesis, GitHub repos, startup tasks, Notion, deliverables, velocity.'

    async def fetch_context(self, user_id: str) -> str:
        if not user_id:
            return 'No user context available.'
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        cutoff_7d = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        cutoff_30d = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

        projects = sb.table('lg_projects').select('name, type, status, deadline, tools') \
            .eq('user_id', user_id).eq('status', 'active') \
            .order('updated_at', desc=True).limit(10).execute()

        commits_7d = sb.table('lg_health').select('value, recorded_at') \
            .eq('user_id', user_id).eq('metric', 'github_commit') \
            .gte('recorded_at', cutoff_7d) \
            .order('recorded_at', desc=True).limit(20).execute()

        commits_prev = sb.table('lg_health').select('value, recorded_at') \
            .eq('user_id', user_id).eq('metric', 'github_commit') \
            .lt('recorded_at', cutoff_7d).gte('recorded_at', cutoff_30d).execute()

        lines = ['=== PROJECTS CONTEXT ===']

        if projects.data:
            lines.append(f'ACTIVE PROJECTS ({len(projects.data)}):')
            for p in projects.data:
                deadline_str = f', deadline {p["deadline"]}' if p.get('deadline') else ''
                lines.append(f'  - {p["name"]} ({p["type"]}){deadline_str}')

        if commits_7d.data:
            repos_this_week = set(c['value'].get('repo', '?') for c in commits_7d.data)
            lines.append(f'COMMIT VELOCITY:')
            lines.append(f'  This week: {len(commits_7d.data)} commits across {len(repos_this_week)} repos')
            if commits_prev.data:
                lines.append(f'  Previous period: {len(commits_prev.data)} commits')
                delta = len(commits_7d.data) - len(commits_prev.data)
                trend = f'+{delta}' if delta >= 0 else str(delta)
                lines.append(f'  Trend: {trend} commits vs previous period')
            lines.append('  Recent commits:')
            for c in commits_7d.data[:5]:
                v = c['value']
                msg = v.get('message', '')[:60]
                lines.append(f'    [{v.get("repo", "?")}] {msg} ({c["recorded_at"][:10]})')
        else:
            lines.append('No commits in the last 7 days.')

        return '\n'.join(lines)

    async def handle(self, request: ChatRequest) -> ChatResponse:
        client = get_client()
        context = await self.build_full_context(request.user_id or '', request.message)

        # Enrich context with tool-sourced velocity trend and stagnant repo flags
        if request.user_id:
            velocity = await get_commit_velocity(request.user_id)
            if velocity.get('trend') not in ('error', None):
                context += (
                    f'\nCOMMIT VELOCITY TREND: {velocity["trend"]} '
                    f'(this week: {velocity["this_week"]}, last week: {velocity["last_week"]}, '
                    f'delta: {velocity["delta"]:+d})'
                )
                if velocity.get('top_repo'):
                    context += f'\n  Most active repo: {velocity["top_repo"]}'

            stagnant = await flag_stagnant_repos(request.user_id, days_threshold=7)
            real_stagnant = [s for s in stagnant if 'error' not in s]
            if real_stagnant:
                context += f'\nSTAGNANT REPOS ({len(real_stagnant)} with no commits this week):'
                for s in real_stagnant:
                    risk_flag = ' [AT RISK]' if s.get('at_risk') else ''
                    context += f'\n  - {s["repo"]}{risk_flag}'

        messages = [{'role': m.role, 'content': m.content} for m in request.history]
        messages.append({'role': 'user', 'content': request.message})

        response = client.messages.create(
            model=AGENT_MODEL,
            max_tokens=512,
            system=f'{self.system_prompt}\n\n{context}',
            messages=messages,
        )
        return ChatResponse(reply=response.content[0].text, agent='Forge')
