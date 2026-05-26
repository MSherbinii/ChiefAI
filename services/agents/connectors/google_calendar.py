"""
Google Calendar connector for Chief.
Syncs upcoming calendar events to the Life Graph.
Events are stored as commitments (deadlines) and facts (scheduled meetings).
"""
import os
import httpx
from datetime import datetime, timezone, timedelta
from supabase import create_client
from connectors.gmail import refresh_google_token  # reuse the same refresh logic

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
CALENDAR_API = 'https://www.googleapis.com/calendar/v3'


async def sync_google_calendar(user_id: str):
    """
    Sync Google Calendar events to the Life Graph.

    What we sync:
    - Upcoming events (next 30 days) → stored as commitments with deadline
    - All-day events → stored as goals with deadline
    - Regular events with attendees → stored as facts (meetings)
    """
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # Get token (same as Gmail — same OAuth flow)
    res = sb.table('connector_tokens').select('*') \
        .eq('user_id', user_id) \
        .eq('connector', 'google_calendar') \
        .maybe_single().execute()

    if not res.data:
        return

    token_row = res.data
    access_token = token_row['access_token']

    # Refresh if expired
    expiry_str = token_row.get('token_expiry')
    if expiry_str:
        expiry = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
        if expiry < datetime.now(timezone.utc):
            new_tokens = await refresh_google_token(token_row['refresh_token'])
            access_token = new_tokens.get('access_token', access_token)
            new_expires_in = new_tokens.get('expires_in', 3600)
            new_expiry = (datetime.now(timezone.utc) + timedelta(seconds=new_expires_in)).isoformat()
            sb.table('connector_tokens').update({
                'access_token': access_token,
                'token_expiry': new_expiry,
            }).eq('user_id', user_id).eq('connector', 'google_calendar').execute()

    sb.table('connector_tokens').update({'sync_status': 'syncing'}) \
        .eq('user_id', user_id).eq('connector', 'google_calendar').execute()

    try:
        now = datetime.now(timezone.utc)
        time_min = now.isoformat()
        time_max = (now + timedelta(days=30)).isoformat()

        async with httpx.AsyncClient() as client:
            events_res = await client.get(
                f'{CALENDAR_API}/calendars/primary/events',
                headers={'Authorization': f'Bearer {access_token}'},
                params={
                    'timeMin': time_min,
                    'timeMax': time_max,
                    'singleEvents': 'true',
                    'orderBy': 'startTime',
                    'maxResults': 50,
                }
            )
            events = events_res.json().get('items', [])

        commitments_created = 0
        facts_created = 0

        for event in events:
            title = event.get('summary', '(no title)')
            description = event.get('description', '')

            # Parse start time
            start = event.get('start', {})
            start_dt = start.get('dateTime') or start.get('date')
            if not start_dt:
                continue

            # Parse end time
            end = event.get('end', {})
            end_dt = end.get('dateTime') or end.get('date')

            # Determine if it's all-day
            is_all_day = 'date' in start and 'dateTime' not in start

            # Get attendees
            attendees = [
                a.get('email', '') for a in event.get('attendees', [])
                if not a.get('self') and a.get('email')
            ]

            # Store as commitment (upcoming event = deadline/task)
            existing = sb.table('commitments') \
                .select('id') \
                .eq('user_id', user_id) \
                .eq('what', title[:200]) \
                .maybe_single().execute()

            if not existing.data:
                try:
                    sb.table('commitments').insert({
                        'user_id': user_id,
                        'agent': 'Chief',
                        'what': title[:200],
                        'why': description[:200] if description else None,
                        'when_due': start_dt,
                        'priority': 'high' if is_all_day else 'normal',
                        'status': 'pending',
                        'assigned_to': 'Chief',
                        'context': {
                            'source': 'google_calendar',
                            'event_id': event.get('id'),
                            'attendees': attendees,
                            'end': end_dt,
                        },
                        'created_at': datetime.now(timezone.utc).isoformat(),
                        'updated_at': datetime.now(timezone.utc).isoformat(),
                    }).execute()
                    commitments_created += 1
                except Exception:
                    pass

            # For events with attendees, also store as a fact in the knowledge graph
            if attendees:
                for attendee_email in attendees[:3]:  # max 3 per event
                    # Try to find/create person entity
                    name = attendee_email.split('@')[0].replace('.', ' ').title()
                    try:
                        entity = sb.table('entities').upsert({
                            'user_id': user_id,
                            'type': 'person',
                            'name': name,
                            'properties': {'email': attendee_email},
                            'source': 'google_calendar',
                            'updated_at': datetime.now(timezone.utc).isoformat(),
                        }, on_conflict='user_id,type,name').execute()

                        if entity.data:
                            entity_id = entity.data[0]['id']
                            sb.table('facts').insert({
                                'user_id': user_id,
                                'subject_id': entity_id,
                                'predicate': 'meeting_on',
                                'object': f'{title[:100]} on {start_dt[:10]}',
                                'confidence': 1.0,
                                'source': 'google_calendar',
                            }).execute()
                            facts_created += 1
                    except Exception:
                        pass

        sb.table('connector_tokens').update({
            'sync_status': 'ok',
            'last_synced_at': datetime.now(timezone.utc).isoformat(),
            'error_message': None,
        }).eq('user_id', user_id).eq('connector', 'google_calendar').execute()

        return {
            'events_processed': len(events),
            'commitments_created': commitments_created,
            'facts_created': facts_created,
        }

    except Exception as e:
        sb.table('connector_tokens').update({
            'sync_status': 'error',
            'error_message': str(e)[:200],
        }).eq('user_id', user_id).eq('connector', 'google_calendar').execute()
        raise
