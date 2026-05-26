"""
Generates a structured Morning Brief from all Life Graph data.
Uses Claude to synthesize health + comms + projects + admin into
a structured JSON brief, then stores it in the briefs table.
"""
import json
import os
from datetime import datetime, timezone, timedelta
from supabase import create_client
from llm import get_client, BRIEF_MODEL

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

BRIEF_PROMPT = """You are Chief, a personal life operating system. Generate a structured Morning Brief
for the user based on the Life Graph data provided.

Return ONLY valid JSON matching this exact schema — no markdown, no prose outside the JSON:
{
  "greeting": "Good morning, [name].",
  "sections": [
    {
      "domain": "body",
      "agent": "Pulse",
      "status": "ok|med|high|crit",
      "headline": "Recovery 72% · Sleep 6h 20m",
      "detail": "Slightly below target. Skip heavy compounds today.",
      "action": "Upper accessories recommended"
    }
  ],
  "life_debt": {
    "total": 5,
    "items": [
      {"domain": "communication", "count": 3, "description": "3 stale emails (2 high priority)"}
    ]
  },
  "best_move": "Send thesis progress update. Your professor email is 5 days old.",
  "patterns": ["Late-night UberEats correlates with lower sleep quality"]
}

Rules:
- Include a section for each domain with data: body (if WHOOP data), work (if commits/comms), admin (if queue items)
- Status: ok = good, med = needs attention, high = urgent, crit = critical
- Life debt: count ALL unresolved items across domains
- Best move: the single highest-impact action for today
- Patterns: cross-domain correlations you notice (only if data supports it — no made-up correlations)
- Be specific: use real numbers, real names, real dates from the data
- Voice: warm, direct, like a mentor — not robotic"""


async def gather_brief_context(sb, user_id: str) -> str:
    """Gather all Life Graph data for brief generation."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    parts = []

    # Health
    rec = sb.table('lg_health').select('value, recorded_at').eq('user_id', user_id) \
        .eq('metric', 'recovery').gte('recorded_at', cutoff) \
        .order('recorded_at', desc=True).limit(1).maybe_single().execute()

    sleep7 = sb.table('lg_health').select('value').eq('user_id', user_id) \
        .eq('metric', 'sleep').gte('recorded_at', cutoff).execute()

    workouts = sb.table('lg_health').select('value, recorded_at').eq('user_id', user_id) \
        .eq('metric', 'workout').gte('recorded_at', cutoff) \
        .order('recorded_at', desc=True).limit(5).execute()

    if rec.data:
        v = rec.data['value']
        parts.append(f'HEALTH: recovery={v.get("recovery_score")}%, '
                     f'HRV={v.get("hrv_rmssd_milli")}ms, '
                     f'RHR={v.get("resting_heart_rate")}bpm '
                     f'(as of {rec.data["recorded_at"][:10]})')

    if sleep7.data:
        avg_min = sum(s['value'].get('duration_minutes', 0) for s in sleep7.data) / len(sleep7.data)
        parts.append(f'SLEEP 7d avg: {avg_min:.0f} min ({avg_min/60:.1f}h)')

    if workouts.data:
        parts.append(f'WORKOUTS this week: {len(workouts.data)}')

    # Communications
    cutoff_3d = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    stale = sb.table('lg_communications').select('subject, channel, last_message_at, participants') \
        .eq('user_id', user_id).eq('status', 'active') \
        .lte('last_message_at', cutoff_3d).order('last_message_at', desc=False).limit(5).execute()

    if stale.data:
        parts.append(f'STALE COMMS ({len(stale.data)} threads):')
        for t in stale.data:
            subj = (t.get('subject') or '(no subject)')[:50]
            staleness = 0
            if t.get('last_message_at'):
                try:
                    lma = datetime.fromisoformat(t['last_message_at'].replace('Z', '+00:00'))
                    staleness = (datetime.now(timezone.utc) - lma).days
                except Exception:
                    pass
            parts.append(f'  [{staleness}d] "{subj}" via {t["channel"]}')

    # Projects
    commits = sb.table('lg_health').select('value, recorded_at').eq('user_id', user_id) \
        .eq('metric', 'github_commit').gte('recorded_at', cutoff) \
        .order('recorded_at', desc=True).limit(10).execute()

    if commits.data:
        repos = set(c['value'].get('repo', '?') for c in commits.data)
        parts.append(f'COMMITS this week: {len(commits.data)} across {len(repos)} repos')

    # Approval queue
    queue = sb.table('approval_queue').select('title, agent, risk_level').eq('user_id', user_id) \
        .eq('status', 'pending').order('created_at', desc=True).limit(5).execute()

    if queue.data:
        parts.append(f'APPROVAL QUEUE ({len(queue.data)} items):')
        for q in queue.data:
            parts.append(f'  [{q["risk_level"]}] {q["title"]} [{q["agent"]}]')

    return '\n'.join(parts) if parts else 'No Life Graph data available yet.'


async def generate_morning_brief(user_id: str, user_name: str = 'there') -> dict:
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    context = await gather_brief_context(sb, user_id)
    today = datetime.now(timezone.utc).date().isoformat()

    client = get_client()
    response = client.messages.create(
        model=BRIEF_MODEL,
        max_tokens=1500,
        system=BRIEF_PROMPT,
        messages=[{
            'role': 'user',
            'content': f'User name: {user_name}\nToday: {today}\n\nLife Graph data:\n{context}'
        }],
    )

    raw = response.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith('```'):
        raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()

    try:
        brief_data = json.loads(raw)
    except json.JSONDecodeError:
        brief_data = {
            'greeting': f'Good morning, {user_name}.',
            'sections': [],
            'life_debt': {'total': 0, 'items': []},
            'best_move': 'Check your connectors — data is still syncing.',
            'patterns': [],
        }

    # Store in briefs table (upsert by date + type)
    sb.table('briefs').upsert({
        'user_id': user_id,
        'brief_date': today,
        'type': 'morning',
        'greeting': brief_data.get('greeting', ''),
        'sections': brief_data.get('sections', []),
        'life_debt': brief_data.get('life_debt', {'total': 0, 'items': []}),
        'best_move': brief_data.get('best_move', ''),
        'patterns': brief_data.get('patterns', []),
        'generated_by': 'bedrock',
        'model': 'amazon.nova-pro-v1:0',
        'created_at': datetime.now(timezone.utc).isoformat(),
    }, on_conflict='user_id,brief_date,type').execute()

    # Store goal_check_in record
    sb.table('goal_check_ins').insert({
        'user_id': user_id,
        'type': 'morning_plan',
        'highlights': [],
        'actions_planned': [brief_data.get('best_move', '')] if brief_data.get('best_move') else [],
        'narrative': brief_data.get('best_move', ''),
        'created_at': datetime.now(timezone.utc).isoformat(),
    }).execute()

    return brief_data
