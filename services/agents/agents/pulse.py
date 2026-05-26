import anthropic
import os
from datetime import datetime, timezone, timedelta
from supabase import create_client
from agents.base import BaseAgent
from models import ChatRequest, ChatResponse

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


class PulseAgent(BaseAgent):
    name = 'Pulse'
    description = 'Health and fitness: recovery, sleep, gym planning, nutrition, weight.'

    async def fetch_context(self, user_id: str) -> str:
        if not user_id:
            return 'No user context available.'
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()

        rec = sb.table('lg_health').select('value, recorded_at') \
            .eq('user_id', user_id).eq('metric', 'recovery') \
            .gte('recorded_at', cutoff) \
            .order('recorded_at', desc=True).limit(1).maybe_single().execute()

        sleeps = sb.table('lg_health').select('value, recorded_at') \
            .eq('user_id', user_id).eq('metric', 'sleep') \
            .gte('recorded_at', cutoff) \
            .order('recorded_at', desc=True).limit(7).execute()

        workouts = sb.table('lg_health').select('value, recorded_at') \
            .eq('user_id', user_id).eq('metric', 'workout') \
            .gte('recorded_at', cutoff) \
            .order('recorded_at', desc=True).limit(10).execute()

        lines = ['=== HEALTH CONTEXT (last 14 days) ===']

        if rec.data:
            v = rec.data['value']
            lines.append(f'Latest recovery: {v.get("recovery_score", "?")}% '
                         f'(HRV: {v.get("hrv_rmssd_milli", "?")} ms, '
                         f'RHR: {v.get("resting_heart_rate", "?")} bpm) '
                         f'recorded {rec.data["recorded_at"][:10]}')

        if sleeps.data:
            avg_dur = sum(s['value'].get('duration_minutes', 0) for s in sleeps.data) / len(sleeps.data)
            avg_eff = sum(s['value'].get('efficiency_pct', 0) for s in sleeps.data) / len(sleeps.data)
            lines.append(f'Sleep 7-day avg: {avg_dur:.0f} min, efficiency {avg_eff:.1f}%')

        if workouts.data:
            lines.append(f'Workouts in last 14 days: {len(workouts.data)}')
            for w in workouts.data[:3]:
                v = w['value']
                lines.append(f'  - {w["recorded_at"][:10]}: strain {v.get("strain", "?")}, '
                              f'{v.get("duration_minutes", "?")} min, '
                              f'avg HR {v.get("average_heart_rate", "?")} bpm')

        if len(lines) == 1:
            return 'No health data available yet. WHOOP not connected or not synced.'

        return '\n'.join(lines)

    async def handle(self, request: ChatRequest) -> ChatResponse:
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        context = await self.fetch_context(request.user_id or '')
        messages = [{'role': m.role, 'content': m.content} for m in request.history]
        messages.append({'role': 'user', 'content': request.message})

        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=512,
            system=f'{self.system_prompt}\n\n{context}',
            messages=messages,
        )
        return ChatResponse(reply=response.content[0].text, agent='Pulse')
