import imaplib
import email
import os
from email.header import decode_header
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from supabase import create_client
from db import safe_single

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


def decode_str(s: str | None) -> str:
    if s is None:
        return ''
    parts = decode_header(s)
    result = []
    for part, enc in parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or 'utf-8', errors='replace'))
        else:
            result.append(str(part))
    return ' '.join(result)


def verify_imap(email_addr: str, password: str, imap_host: str, imap_port: int = 993) -> bool:
    try:
        mail = imaplib.IMAP4_SSL(imap_host, imap_port)
        mail.login(email_addr, password)
        mail.logout()
        return True
    except Exception:
        return False


async def sync_imap(user_id: str):
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    res = safe_single(sb.table('connector_tokens').select('*').eq('user_id', user_id).eq('connector', 'imap_uni').maybe_single())
    if not res.data:
        return

    token_row = res.data
    extra = token_row.get('extra') or {}
    email_addr = extra.get('email', '')
    password = token_row['access_token']
    imap_host = extra.get('imap_host', '')
    imap_port = int(extra.get('imap_port', 993))

    sb.table('connector_tokens').update({'sync_status': 'syncing'}).eq('user_id', user_id).eq('connector', 'imap_uni').execute()

    try:
        mail = imaplib.IMAP4_SSL(imap_host, imap_port)
        mail.login(email_addr, password)
        mail.select('INBOX')

        _, msg_nums = mail.search(None, 'ALL')
        all_nums = msg_nums[0].split() if msg_nums[0] else []
        recent = all_nums[-30:] if len(all_nums) > 30 else all_nums

        for num in reversed(recent):
            _, data = mail.fetch(num, '(BODY[HEADER.FIELDS (FROM TO SUBJECT DATE MESSAGE-ID)])')
            if not data or not data[0]:
                continue
            raw = data[0][1]
            msg = email.message_from_bytes(raw)

            subject = decode_str(msg.get('Subject', ''))
            from_addr = decode_str(msg.get('From', ''))
            date_str = msg.get('Date', '')
            msg_id = msg.get('Message-ID', str(num))

            try:
                dt = parsedate_to_datetime(date_str).astimezone(timezone.utc).isoformat()
            except Exception:
                dt = datetime.now(timezone.utc).isoformat()

            sb.table('lg_communications').upsert({
                'user_id': user_id,
                'thread_id': f'imap_{msg_id.strip("<>")}',
                'channel': 'imap_uni',
                'participants': [from_addr],
                'subject': subject,
                'last_message_at': dt,
                'status': 'active',
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }, on_conflict='user_id,thread_id').execute()

        mail.logout()

        sb.table('connector_tokens').update({
            'sync_status': 'ok',
            'last_synced_at': datetime.now(timezone.utc).isoformat(),
            'error_message': None,
        }).eq('user_id', user_id).eq('connector', 'imap_uni').execute()

    except Exception as e:
        sb.table('connector_tokens').update({
            'sync_status': 'error',
            'error_message': str(e)[:200],
        }).eq('user_id', user_id).eq('connector', 'imap_uni').execute()
        raise
