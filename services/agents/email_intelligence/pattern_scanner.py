"""
Pattern-First Scanner — detects disputes, billing failures, legal threats,
and important correspondence by scanning ALL emails for known patterns.

Unlike case_discoverer.py which starts from entities, this starts from
email content patterns and builds cases from what it finds.

This is the zero-shot, provider-agnostic intelligence layer:
- No hardcoded entity names
- Detects patterns that MATTER to the user
- Works for any inbox regardless of language/country
"""
import os
import json
import re
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from supabase import create_client
from llm import get_client, BRIEF_MODEL, AGENT_MODEL

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


# ─── Pattern Definitions ──────────────────────────────────────────────────────

DISPUTE_PATTERNS = [
    # German
    r'mahnung', r'mahnbescheid', r'inkasso', r'forderung', r'schulden',
    r'vollstreckung', r'klage', r'anwalt', r'rechtlich', r'zahlungsaufforderung',
    r'letzte mahnung', r'offene rechnung', r'r.ckstand',
    r'k.ndigung', r'widerspruch', r'beschwerde',
    # English
    r'debt collect', r'collection agenc', r'overdue', r'past due',
    r'legal action', r'attorney', r'lawsuit', r'default',
    r'final notice', r'demand letter', r'account in arrears',
]

BILLING_FAILURE_PATTERNS = [
    r'zahlung.{0,20}fehlgeschlagen', r'zahlung.{0,20}abgelehnt',
    r'payment.{0,20}fail', r'payment.{0,20}declin', r'payment.{0,20}reject',
    r'unable to.{0,20}charge', r'card.{0,20}declin',
    r'subscription.{0,20}cancel', r'service.{0,20}suspend',
    r'auftrag.{0,20}nicht.{0,20}ausgef', r'bestellung.{0,20}storniert',
]

STALLED_APPLICATION_PATTERNS = [
    r'application.{0,20}pending', r'application.{0,20}review',
    r'antrag.{0,20}bearbeitung', r'antrag.{0,20}gepr.ft',
    r'awaiting.{0,20}verification', r'verification.{0,20}required',
    r'dokument.{0,20}fehlt', r'nachweis.{0,20}erforderlich',
    r'account.{0,20}setup.{0,20}incomplete', r'konto.{0,20}unvollst.ndig',
]

URGENT_PATTERNS = [
    r'dringend', r'urgent', r'sofort', r'immediately', r'last chance',
    r'letzte chance', r'frist', r'deadline', r'bis.{0,10}\d+\.\d+\.',
    r'within \d+ days', r'innerhalb von \d+ tagen',
]

GOVERNMENT_PATTERNS = [
    r'finanzamt', r'jobcenter', r'ausl.nderbeh.rde', r'zoll',
    r'bundesagentur', r'beh.rde', r'amt ', r'meldebeh.rde',
    r'anmeldung', r'immatrikulation', r'visa', r'aufenthaltstitel',
]


def _compute_pattern_score(text: str) -> dict:
    """Score an email text against all pattern categories."""
    text_lower = text.lower()
    scores = {
        'dispute': sum(1 for p in DISPUTE_PATTERNS if re.search(p, text_lower)),
        'billing_failure': sum(1 for p in BILLING_FAILURE_PATTERNS if re.search(p, text_lower)),
        'stalled_application': sum(1 for p in STALLED_APPLICATION_PATTERNS if re.search(p, text_lower)),
        'urgent': sum(1 for p in URGENT_PATTERNS if re.search(p, text_lower)),
        'government': sum(1 for p in GOVERNMENT_PATTERNS if re.search(p, text_lower)),
    }
    scores['total'] = sum(scores.values())
    return scores


async def scan_for_patterns(user_id: str, lookback_days: int = 1095) -> list[dict]:
    """
    Scan ALL emails for high-signal patterns.
    Returns list of flagged email groups sorted by importance.
    lookback_days: how far back to scan (default 3 years = 1095 days)
    """
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).isoformat()

    # Fetch all emails with body text
    emails = sb.table('email_raw').select(
        'id, gmail_id, from_email, subject, body_text, snippet, date, is_sent, thread_id'
    ).eq('user_id', user_id).gte('date', cutoff).execute()

    if not emails.data:
        return []

    # Score each email
    flagged = []
    for email in emails.data:
        text = (email.get('subject') or '') + ' ' + (email.get('body_text') or '') + ' ' + (email.get('snippet') or '')
        scores = _compute_pattern_score(text)

        if scores['total'] >= 2 or scores['dispute'] >= 1 or scores['urgent'] >= 1:
            flagged.append({
                'email': email,
                'scores': scores,
                'importance': scores['dispute'] * 3 + scores['billing_failure'] * 2 + scores['urgent'] * 2 + scores['government'] * 2 + scores['stalled_application'],
            })

    # Group by sender domain (thread clustering)
    domain_groups = defaultdict(list)
    for item in flagged:
        from_email = item['email'].get('from_email', '')
        domain = from_email.split('@')[-1].lower() if '@' in from_email else from_email
        domain_groups[domain].append(item)

    # Sort groups by total importance
    result = []
    for domain, items in domain_groups.items():
        total_importance = sum(i['importance'] for i in items)
        if total_importance < 2:
            continue

        # Get sample emails for this domain
        sample_emails = sorted(items, key=lambda x: x['email'].get('date', ''), reverse=True)[:5]

        result.append({
            'domain': domain,
            'email_count': len(items),
            'total_importance': total_importance,
            'primary_category': max(['dispute', 'billing_failure', 'stalled_application', 'government'],
                                   key=lambda c: sum(i['scores'][c] for i in items)),
            'sample_emails': [
                {
                    'date': e['email']['date'][:10],
                    'subject': (e['email'].get('subject') or '')[:80],
                    'from': e['email'].get('from_email', '')[:50],
                    'is_sent': e['email'].get('is_sent', False),
                    'scores': e['scores'],
                }
                for e in sample_emails
            ],
            'all_ids': [i['email']['id'] for i in items],
        })

    result.sort(key=lambda x: x['total_importance'], reverse=True)
    return result


CASE_FROM_PATTERN_PROMPT = """You are analyzing a group of emails from ONE organization that triggered dispute/billing/legal pattern detection.

Create a structured CASE if these emails represent an actionable situation requiring the user's attention.

Domain: {domain}
Email count: {email_count}
Primary detected pattern: {primary_category}

Sample emails (newest first):
{email_samples}

If this IS a case, return JSON:
{{
  "is_case": true,
  "title": "Brief case title (max 60 chars)",
  "status": "open|progressing|stalled|needs_action|resolved",
  "priority": "low|normal|high|critical",
  "category": "dispute|billing|account_setup|application|government|service_issue|other",
  "summary": "2-3 sentence summary of the situation",
  "pending_action": "What the user needs to do (null if nothing)",
  "stalled_since": "ISO date if stalled (null otherwise)",
  "confidence": 0.0-1.0,
  "timeline": [{{"date": "YYYY-MM-DD", "event": "description", "direction": "sent|received"}}]
}}

If this is NOT worth a case (just spam, newsletters, routine billing):
{{"is_case": false, "reason": "brief explanation"}}

Return ONLY valid JSON."""


async def create_cases_from_patterns(user_id: str) -> dict:
    """
    Full pipeline: scan patterns → group by domain → run Sonnet on high-signal groups → save cases.
    """
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    client = get_client()

    # Find high-signal email groups
    pattern_groups = await scan_for_patterns(user_id)

    if not pattern_groups:
        return {'user_id': user_id, 'groups_analyzed': 0, 'cases_created': 0}

    cases_created = 0
    cases_updated = 0
    groups_analyzed = 0

    for group in pattern_groups[:50]:  # Process top 50 groups
        groups_analyzed += 1
        domain = group['domain']
        samples = group['sample_emails']

        email_lines = []
        for e in samples:
            direction = 'YOU SENT' if e['is_sent'] else 'RECEIVED'
            email_lines.append(f"[{e['date']}] {direction}: {e['subject']}")

        prompt = CASE_FROM_PATTERN_PROMPT.format(
            domain=domain,
            email_count=group['email_count'],
            primary_category=group['primary_category'],
            email_samples='\n'.join(email_lines),
        )

        try:
            response = client.messages.create(
                model=BRIEF_MODEL,  # Sonnet for quality case reasoning
                max_tokens=800,
                messages=[{'role': 'user', 'content': prompt}],
            )
            raw = response.content[0].text.strip()
            if raw.startswith('```'):
                raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()

            result = json.loads(raw)

            if not result.get('is_case'):
                continue

            confidence = result.get('confidence', 0.5)
            if confidence < 0.5:
                continue

            title = result['title'][:200]

            # Check if case already exists
            existing = sb.table('email_cases').select('id').eq('user_id', user_id) \
                .eq('title', title).maybe_single().execute()

            case_data = {
                'user_id': user_id,
                'title': title,
                'status': result.get('status', 'open'),
                'priority': result.get('priority', 'normal'),
                'category': result.get('category'),
                'summary': result.get('summary'),
                'pending_action': result.get('pending_action'),
                'stalled_since': result.get('stalled_since'),
                'timeline': result.get('timeline', []),
                'confidence': confidence,
                'email_ids': group['all_ids'][:50],
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }

            if existing.data:
                sb.table('email_cases').update(case_data).eq('id', existing.data['id']).execute()
                cases_updated += 1
            else:
                case_data['created_at'] = datetime.now(timezone.utc).isoformat()
                sb.table('email_cases').insert(case_data).execute()
                cases_created += 1

        except Exception:
            continue

    return {
        'user_id': user_id,
        'groups_analyzed': groups_analyzed,
        'cases_created': cases_created,
        'cases_updated': cases_updated,
    }
