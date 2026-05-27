# services/agents/email/deep_scanner.py
"""
Full Gmail inbox deep scanner.
Fetches ALL emails via pagination (not just recent 50).
Stores in email_raw for downstream intelligence processing.
Also fetches SENT folder — critical for case detection.
"""
import os
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
import httpx
from supabase import create_client
from connectors.gmail import refresh_google_token

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
GMAIL_API = 'https://gmail.googleapis.com/gmail/v1'


async def _get_valid_token(user_id: str) -> Optional[str]:
    """Get a valid access token, refreshing if expired."""
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    from db import safe_single
    res = safe_single(sb.table('connector_tokens').select('*')
        .eq('user_id', user_id).eq('connector', 'gmail')
        .maybe_single())

    if not res.data:
        return None

    token_row = res.data
    access_token = token_row['access_token']

    expiry_str = token_row.get('token_expiry')
    if expiry_str:
        expiry = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
        if expiry < datetime.now(timezone.utc):
            new_tokens = await refresh_google_token(token_row['refresh_token'])
            if new_tokens.get('error'):
                # Token refresh failed — log it and return None to surface the error
                _update_scan_status(sb, user_id,
                    status='error',
                    error_message=f"Gmail token refresh failed: {new_tokens.get('error')} - {new_tokens.get('error_description', '')}"
                )
                return None
            access_token = new_tokens.get('access_token', access_token)
            new_expiry = (datetime.now(timezone.utc) + timedelta(seconds=new_tokens.get('expires_in', 3600))).isoformat()
            sb.table('connector_tokens').update({
                'access_token': access_token,
                'token_expiry': new_expiry,
            }).eq('user_id', user_id).eq('connector', 'gmail').execute()

    return access_token


def _update_scan_status(sb, user_id: str, **kwargs):
    """Update scan progress in email_scan_status."""
    kwargs['updated_at'] = datetime.now(timezone.utc).isoformat()
    try:
        sb.table('email_scan_status').upsert(
            {'user_id': user_id, **kwargs},
            on_conflict='user_id'
        ).execute()
    except Exception:
        pass


def _parse_message(msg: dict, user_id: str) -> Optional[dict]:
    """Parse Gmail API message into email_raw row."""
    payload = msg.get('payload', {})
    headers = {h['name'].lower(): h['value'] for h in payload.get('headers', [])}

    from_raw = headers.get('from', '')
    from_parts = from_raw.split('<')
    if len(from_parts) == 2:
        from_name = from_parts[0].strip().strip('"')
        from_email = from_parts[1].rstrip('>').strip().lower()
    else:
        from_email = from_raw.strip().lower()
        from_name = from_email.split('@')[0] if '@' in from_email else from_raw

    to_raw = headers.get('to', '')
    to_emails = [e.strip().lower() for e in to_raw.split(',') if '@' in e]

    date_str = headers.get('date', '')
    try:
        from email.utils import parsedate_to_datetime
        date = parsedate_to_datetime(date_str).astimezone(timezone.utc)
    except Exception:
        date = datetime.now(timezone.utc)

    labels = msg.get('labelIds', [])
    is_sent = 'SENT' in labels
    is_read = 'UNREAD' not in labels

    body_text = ''
    snippet = msg.get('snippet', '')[:500]

    def extract_body(part):
        nonlocal body_text
        if part.get('mimeType') == 'text/plain':
            import base64
            data = part.get('body', {}).get('data', '')
            if data:
                try:
                    body_text = base64.urlsafe_b64decode(data + '==').decode('utf-8', errors='replace')[:2000]
                except Exception:
                    pass
        for sub in part.get('parts', []):
            extract_body(sub)

    extract_body(payload)
    if not body_text:
        body_text = snippet

    internal_date = msg.get('internalDate')
    if internal_date:
        date = datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc)

    return {
        'user_id': user_id,
        'gmail_id': msg['id'],
        'thread_id': msg.get('threadId', ''),
        'from_email': from_email,
        'from_name': from_name or None,
        'to_emails': to_emails,
        'subject': headers.get('subject', '')[:500],
        'snippet': snippet,
        'body_text': body_text,
        'date': date.isoformat(),
        'labels': labels,
        'is_sent': is_sent,
        'is_read': is_read,
        'has_attachments': bool(payload.get('parts', [])),
        'in_reply_to': headers.get('in-reply-to') or None,
        'processed': False,
    }


async def deep_scan_inbox(user_id: str) -> dict:
    """
    Scan ALL emails in user's Gmail account.
    Fetches inbox + sent + starred, deduplicates, stores in email_raw.
    """
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    access_token = await _get_valid_token(user_id)

    if not access_token:
        _update_scan_status(sb, user_id, status='error', error_message='No Gmail access token found')
        return {'error': 'No Gmail token'}

    _update_scan_status(sb, user_id,
        status='scanning',
        started_at=datetime.now(timezone.utc).isoformat(),
        scanned_emails=0, total_emails=0
    )

    query_sets = ['in:inbox', 'in:sent', 'is:starred']
    all_message_ids = set()

    async with httpx.AsyncClient(timeout=30) as client:
        auth_headers = {'Authorization': f'Bearer {access_token}'}

        # Phase 1: collect all message IDs
        for query in query_sets:
            page_token = None
            while True:
                params = {'q': query, 'maxResults': 500}
                if page_token:
                    params['pageToken'] = page_token

                resp = await client.get(f'{GMAIL_API}/users/me/messages', headers=auth_headers, params=params)
                if resp.status_code != 200:
                    break

                data = resp.json()
                for m in data.get('messages', []):
                    all_message_ids.add(m['id'])

                page_token = data.get('nextPageToken')
                if not page_token:
                    break

        total = len(all_message_ids)
        _update_scan_status(sb, user_id, total_emails=total)

        # Phase 2: fetch full messages in batches of 25
        msg_id_list = list(all_message_ids)
        batch_size = 25
        saved = 0
        errors = 0
        total_fetched = 0

        for i in range(0, len(msg_id_list), batch_size):
            batch = msg_id_list[i:i + batch_size]
            tasks = [
                client.get(
                    f'{GMAIL_API}/users/me/messages/{mid}',
                    headers=auth_headers,
                    params={'format': 'full'}
                )
                for mid in batch
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            rows = []
            for resp in responses:
                if isinstance(resp, Exception):
                    errors += 1
                    continue
                if resp.status_code != 200:
                    errors += 1
                    continue
                try:
                    row = _parse_message(resp.json(), user_id)
                    if row:
                        rows.append(row)
                except Exception:
                    errors += 1

            if rows:
                try:
                    sb.table('email_raw').upsert(rows, on_conflict='user_id,gmail_id').execute()
                    saved += len(rows)
                except Exception:
                    pass

            total_fetched += len(batch)
            _update_scan_status(sb, user_id, scanned_emails=total_fetched)
            await asyncio.sleep(0.1)

    _update_scan_status(sb, user_id, status='clustering', scanned_emails=total_fetched)

    return {
        'user_id': user_id,
        'total_found': total,
        'saved': saved,
        'errors': errors,
    }


async def get_scan_status(user_id: str) -> dict:
    """Get current scan progress for a user."""
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    from db import safe_single
    res = safe_single(sb.table('email_scan_status').select('*').eq('user_id', user_id).maybe_single())
    if not res.data:
        return {'status': 'idle', 'user_id': user_id}
    return res.data
