import httpx
import os
from datetime import datetime, timezone
from supabase import create_client

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


async def refresh_google_token(refresh_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.post('https://oauth2.googleapis.com/token', data={
            'client_id': os.getenv('GOOGLE_CLIENT_ID'),
            'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
        })
        return r.json()


async def sync_gmail(user_id: str):
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    res = sb.table('connector_tokens').select('*').eq('user_id', user_id).eq('connector', 'gmail').maybe_single().execute()
    if not res.data:
        return

    token_row = res.data
    access_token = token_row['access_token']

    expiry_str = token_row.get('token_expiry')
    if expiry_str:
        expiry = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
        if expiry < datetime.now(timezone.utc):
            new_tokens = await refresh_google_token(token_row['refresh_token'])
            access_token = new_tokens.get('access_token', access_token)
            sb.table('connector_tokens').update({
                'access_token': access_token,
                'token_expiry': datetime.now(timezone.utc).isoformat(),
            }).eq('user_id', user_id).eq('connector', 'gmail').execute()

    sb.table('connector_tokens').update({'sync_status': 'syncing'}).eq('user_id', user_id).eq('connector', 'gmail').execute()

    try:
        async with httpx.AsyncClient() as client:
            threads_res = await client.get(
                'https://gmail.googleapis.com/gmail/v1/users/me/threads',
                headers={'Authorization': f'Bearer {access_token}'},
                params={'maxResults': 50, 'q': 'newer_than:30d'},
            )
            threads = threads_res.json().get('threads', [])

        for thread in threads[:20]:
            async with httpx.AsyncClient() as client:
                detail_res = await client.get(
                    f'https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread["id"]}',
                    headers={'Authorization': f'Bearer {access_token}'},
                    params={'format': 'metadata', 'metadataHeaders': ['From', 'Subject', 'Date']},
                )
            detail = detail_res.json()
            messages = detail.get('messages', [])
            if not messages:
                continue

            last_msg = messages[-1]
            headers_list = last_msg.get('payload', {}).get('headers', [])
            headers_map = {h['name']: h['value'] for h in headers_list}
            subject = headers_map.get('Subject', '(no subject)')
            from_addr = headers_map.get('From', '')
            date_str = headers_map.get('Date', '')

            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(date_str).astimezone(timezone.utc).isoformat()
            except Exception:
                dt = datetime.now(timezone.utc).isoformat()

            sb.table('lg_communications').upsert({
                'user_id': user_id,
                'thread_id': thread['id'],
                'channel': 'gmail',
                'participants': [from_addr],
                'subject': subject,
                'last_message_at': dt,
                'status': 'active',
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }, on_conflict='user_id,thread_id').execute()

        sb.table('connector_tokens').update({
            'sync_status': 'ok',
            'last_synced_at': datetime.now(timezone.utc).isoformat(),
            'error_message': None,
        }).eq('user_id', user_id).eq('connector', 'gmail').execute()

    except Exception as e:
        sb.table('connector_tokens').update({
            'sync_status': 'error',
            'error_message': str(e)[:200],
        }).eq('user_id', user_id).eq('connector', 'gmail').execute()
        raise
