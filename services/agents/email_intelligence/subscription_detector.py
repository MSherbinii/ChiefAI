# services/agents/email_intelligence/subscription_detector.py
"""
Detects newsletter/subscription emails from email_raw using pattern matching.
No LLM needed — uses frequency, unsubscribe link detection, and engagement signals.
"""
import os
import re
from datetime import datetime, timezone
from collections import defaultdict
from supabase import create_client

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

NEWSLETTER_PATTERNS = [
    r'list-unsubscribe',
    r'unsubscribe',
    r'abbestellen',
    r'vom\s+newsletter\s+abmelden',
    r'newsletter.*abmelden',
    r'noreply@',
    r'no-reply@',
    r'donotreply@',
    r'mailer@',
    r'newsletter@',
    r'marketing@',
    r'updates@',
    r'notifications@',
    r'info@.*\.(de|com)',
]

NEWSLETTER_SUBJECTS = [
    r'newsletter',
    r'angebot',
    r'sale',
    r'% off',
    r'new arrivals',
    r'weekly digest',
    r'monthly update',
    r'breaking news',
    r'your weekly',
    r'this week in',
    r'top stories',
]


def _has_unsubscribe_link(snippet: str, body_text: str) -> tuple[bool, str]:
    """Detect unsubscribe link in email content."""
    content = (snippet or '') + (body_text or '')
    content_lower = content.lower()

    for pattern in NEWSLETTER_PATTERNS:
        match = re.search(pattern, content_lower)
        if match:
            url_match = re.search(
                r'https?://[^\s<>"]+(?:unsubscribe|abbestell|abmeld)[^\s<>"]*',
                content, re.IGNORECASE
            )
            url = url_match.group(0)[:500] if url_match else None
            return True, url or ''

    return False, ''


def _has_newsletter_subject(subject: str) -> bool:
    """Check if subject suggests newsletter."""
    if not subject:
        return False
    subject_lower = subject.lower()
    return any(re.search(p, subject_lower) for p in NEWSLETTER_SUBJECTS)


async def detect_subscriptions(user_id: str) -> dict:
    """
    Analyze email_raw to find subscription/newsletter senders.
    Creates email_subscriptions rows with engagement scores.
    Updates scan_status to 'complete' when done.
    """
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    rows = sb.table('email_raw').select(
        'from_email, from_name, subject, snippet, body_text, date, is_read, is_sent, labels'
    ).eq('user_id', user_id).eq('is_sent', False).execute()

    if not rows.data:
        _mark_complete(sb, user_id)
        return {'user_id': user_id, 'subscriptions_found': 0}

    sender_data = defaultdict(lambda: {
        'name': '', 'dates': [], 'read_count': 0, 'total_count': 0,
        'has_unsubscribe': False, 'unsubscribe_url': '',
        'newsletter_subject_count': 0,
    })

    for r in rows.data:
        email = r.get('from_email', '').lower()
        if not email:
            continue

        sd = sender_data[email]
        sd['name'] = r.get('from_name', '') or sd['name']
        sd['total_count'] += 1

        if r.get('date'):
            sd['dates'].append(r['date'])

        if r.get('is_read'):
            sd['read_count'] += 1

        if not sd['has_unsubscribe']:
            has_unsub, url = _has_unsubscribe_link(
                r.get('snippet', ''), r.get('body_text', '')
            )
            if has_unsub:
                sd['has_unsubscribe'] = True
                sd['unsubscribe_url'] = url

        if _has_newsletter_subject(r.get('subject', '')):
            sd['newsletter_subject_count'] += 1

    subscriptions_created = 0

    for sender_email, sd in sender_data.items():
        total = sd['total_count']
        if total < 3:
            continue

        dates = sorted(sd['dates'])
        avg_interval_days = None
        frequency = 'irregular'
        if len(dates) >= 2:
            try:
                d1 = datetime.fromisoformat(dates[0].replace('Z', '+00:00'))
                d2 = datetime.fromisoformat(dates[-1].replace('Z', '+00:00'))
                span_days = (d2 - d1).days
                avg_interval = span_days / (len(dates) - 1)
                avg_interval_days = round(avg_interval, 1)
                if avg_interval <= 2:
                    frequency = 'daily'
                elif avg_interval <= 10:
                    frequency = 'weekly'
                elif avg_interval <= 35:
                    frequency = 'monthly'
                else:
                    frequency = 'irregular'
            except Exception:
                pass

        newsletter_signals = 0
        if sd['has_unsubscribe']:
            newsletter_signals += 3
        if total > 0 and sd['newsletter_subject_count'] / total > 0.3:
            newsletter_signals += 2
        if total >= 5:
            newsletter_signals += 1

        if newsletter_signals < 2:
            continue

        # Calculate staleness: how many days since last email
        staleness_days = 0
        if dates:
            try:
                last_date = datetime.fromisoformat(dates[-1].replace('Z', '+00:00'))
                staleness_days = (datetime.now(timezone.utc) - last_date).days
            except Exception:
                pass

        # Revised engagement: penalize based on staleness
        # 0 = stale (>365 days old), 1 = active (recent)
        if staleness_days > 365:
            engagement_score = 0.0  # Dead subscription
        elif staleness_days > 90:
            engagement_score = 0.2  # Probably unwanted
        elif staleness_days > 30:
            engagement_score = round(sd['read_count'] / total, 2) * 0.6 if total > 0 else 0.0  # Partial
        else:
            engagement_score = round(sd['read_count'] / total, 2) if total > 0 else 0.0  # Recent

        entity_res = None
        if '@' in sender_email:
            domain = sender_email.split('@')[1]
            try:
                entity_res = sb.table('entities').select('id') \
                    .eq('user_id', user_id) \
                    .contains('email_domains', [domain]) \
                    .maybe_single().execute()
            except Exception:
                pass
        entity_id = entity_res.data['id'] if (entity_res and entity_res.data) else None

        try:
            sb.table('email_subscriptions').upsert({
                'user_id': user_id,
                'entity_id': entity_id,
                'sender_email': sender_email,
                'sender_name': sd['name'] or None,
                'frequency': frequency,
                'avg_interval_days': avg_interval_days,
                'total_received': total,
                'last_received': dates[-1] if dates else None,
                'opened_count': sd['read_count'],
                'replied_count': 0,
                'engagement_score': engagement_score,
                'has_unsubscribe_link': sd['has_unsubscribe'],
                'unsubscribe_url': sd['unsubscribe_url'] or None,
                'status': 'active',
                'user_decision': 'undecided',
            }, on_conflict='user_id,sender_email').execute()
            subscriptions_created += 1
        except Exception:
            pass

    _mark_complete(sb, user_id)

    return {
        'user_id': user_id,
        'senders_analyzed': len(sender_data),
        'subscriptions_found': subscriptions_created,
    }


def _mark_complete(sb, user_id: str):
    """Mark scan as complete."""
    try:
        sb.table('email_scan_status').update({
            'status': 'complete',
            'completed_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }).eq('user_id', user_id).execute()
    except Exception:
        pass
