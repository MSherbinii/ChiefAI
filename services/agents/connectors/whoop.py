import httpx
import os
from datetime import datetime, timezone
from supabase import create_client

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
WHOOP_API = 'https://api.prod.whoop.com/developer/v1'


async def refresh_whoop_token(refresh_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.post('https://api.prod.whoop.com/oauth/oauth2/token', data={
            'client_id': os.getenv('WHOOP_CLIENT_ID'),
            'client_secret': os.getenv('WHOOP_CLIENT_SECRET'),
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
        })
        return r.json()


async def sync_whoop(user_id: str):
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    res = sb.table('connector_tokens').select('*').eq('user_id', user_id).eq('connector', 'whoop').maybe_single().execute()
    if not res.data:
        return

    token_row = res.data
    access_token = token_row['access_token']

    expiry_str = token_row.get('token_expiry')
    if expiry_str:
        expiry = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
        if expiry < datetime.now(timezone.utc):
            new_tokens = await refresh_whoop_token(token_row['refresh_token'])
            access_token = new_tokens.get('access_token', access_token)
            sb.table('connector_tokens').update({
                'access_token': access_token,
                'token_expiry': datetime.now(timezone.utc).isoformat(),
            }).eq('user_id', user_id).eq('connector', 'whoop').execute()

    sb.table('connector_tokens').update({'sync_status': 'syncing'}).eq('user_id', user_id).eq('connector', 'whoop').execute()
    auth_headers = {'Authorization': f'Bearer {access_token}'}

    try:
        async with httpx.AsyncClient() as client:
            sleep_res = await client.get(f'{WHOOP_API}/activity/sleep', headers=auth_headers, params={'limit': 7})
            sleeps = sleep_res.json().get('records', []) if sleep_res.status_code == 200 else []

            recovery_res = await client.get(f'{WHOOP_API}/recovery', headers=auth_headers, params={'limit': 7})
            recoveries = recovery_res.json().get('records', []) if recovery_res.status_code == 200 else []

            workout_res = await client.get(f'{WHOOP_API}/activity/workout', headers=auth_headers, params={'limit': 10})
            workouts = workout_res.json().get('records', []) if workout_res.status_code == 200 else []

        for sleep in sleeps:
            score = sleep.get('score') or {}
            start = sleep.get('start', '')
            if not start:
                continue
            stage = score.get('stage_summary') or {}
            sb.table('lg_health').upsert({
                'user_id': user_id,
                'metric': 'sleep',
                'value': {
                    'duration_minutes': stage.get('total_in_bed_time_milli', 0) // 60000,
                    'efficiency_pct': score.get('sleep_efficiency_percentage', 0),
                    'quality': score.get('sleep_performance_percentage', 0),
                },
                'source': 'whoop',
                'confidence': 'high',
                'recorded_at': start,
            }, on_conflict='user_id,metric,recorded_at').execute()

        for rec in recoveries:
            created = rec.get('created_at', '')
            if not created:
                continue
            score = rec.get('score') or {}
            sb.table('lg_health').upsert({
                'user_id': user_id,
                'metric': 'recovery',
                'value': {
                    'recovery_score': score.get('recovery_score', 0),
                    'hrv_rmssd_milli': score.get('hrv_rmssd_milli', 0),
                    'resting_heart_rate': score.get('resting_heart_rate_bpm', 0),
                    'spo2_pct': score.get('spo2_percentage', 0),
                },
                'source': 'whoop',
                'confidence': 'high',
                'recorded_at': created,
            }, on_conflict='user_id,metric,recorded_at').execute()

        for workout in workouts:
            start = workout.get('start', '')
            if not start:
                continue
            end = workout.get('end', start)
            score = workout.get('score') or {}
            try:
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                duration_min = int((end_dt - start_dt).total_seconds() // 60)
            except Exception:
                duration_min = 0

            sb.table('lg_health').upsert({
                'user_id': user_id,
                'metric': 'workout',
                'value': {
                    'sport_id': workout.get('sport_id', 0),
                    'strain': score.get('strain', 0),
                    'average_heart_rate': score.get('average_heart_rate_bpm', 0),
                    'max_heart_rate': score.get('max_heart_rate_bpm', 0),
                    'calories': round((score.get('kilojoule', 0) or 0) / 4.184, 1),
                    'duration_minutes': duration_min,
                },
                'source': 'whoop',
                'confidence': 'high',
                'recorded_at': start,
            }, on_conflict='user_id,metric,recorded_at').execute()

        sb.table('connector_tokens').update({
            'sync_status': 'ok',
            'last_synced_at': datetime.now(timezone.utc).isoformat(),
            'error_message': None,
        }).eq('user_id', user_id).eq('connector', 'whoop').execute()

    except Exception as e:
        sb.table('connector_tokens').update({
            'sync_status': 'error',
            'error_message': str(e)[:200],
        }).eq('user_id', user_id).eq('connector', 'whoop').execute()
        raise
