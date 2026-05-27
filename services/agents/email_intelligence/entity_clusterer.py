# services/agents/email_intelligence/entity_clusterer.py
"""
Groups email_raw rows by sender domain, creates/updates entities,
and uses Haiku to classify relationship_type for each entity.
"""
import os
import json
from datetime import datetime, timezone
from collections import defaultdict
from supabase import create_client
from llm import get_client, AGENT_MODEL

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

CLASSIFY_SYSTEM = """You classify email senders by their relationship to the user.
Given a list of email addresses from the same organization, return JSON:
{
  "entity_name": "Deutsche Bank",
  "relationship_type": "bank",
  "confidence": 0.95
}

relationship_type must be ONE of: service_provider, bank, debt_collector, employer,
professor, newsletter, marketplace, government, friend, unknown

Rules:
- debt_collector: inkasso, collections, mahnung, schulden, forderung in domain/name
- bank: bank, sparkasse, volksbank, commerzbank, ing, n26, revolut, wise
- government: finanzamt, bafin, bundesagentur, jobcenter, rathaus, amt
- newsletter: unsubscribe patterns, marketing domains, noreply-only senders
- marketplace: amazon, ebay, etsy, otto, zalando
- Return ONLY valid JSON, no prose"""


def _extract_domain(email: str) -> str:
    """Extract domain from email address."""
    if '@' in email:
        return email.split('@')[1].lower()
    return email.lower()


def _is_personal_email(domain: str) -> bool:
    """Personal email providers should not be grouped as entities."""
    personal_domains = {
        'gmail.com', 'googlemail.com', 'yahoo.com', 'yahoo.de',
        'hotmail.com', 'outlook.com', 'live.com', 't-online.de',
        'web.de', 'gmx.de', 'gmx.net', 'icloud.com', 'me.com',
    }
    return domain in personal_domains


async def cluster_entities(user_id: str) -> dict:
    """
    Group email_raw by sender domain → create entities → classify with Haiku.
    Updates email_scan_status to 'detecting_subscriptions' when done.
    """
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    client = get_client()

    rows = sb.table('email_raw').select('from_email, from_name, date, is_sent') \
        .eq('user_id', user_id).execute()

    domain_senders = defaultdict(lambda: {
        'emails': set(), 'names': set(), 'dates': [],
        'sent_count': 0, 'received_count': 0
    })

    for r in (rows.data or []):
        email = r.get('from_email', '')
        name = r.get('from_name', '')
        domain = _extract_domain(email)

        key = email if _is_personal_email(domain) else domain

        domain_senders[key]['emails'].add(email)
        if name:
            domain_senders[key]['names'].add(name)
        if r.get('date'):
            domain_senders[key]['dates'].append(r['date'])
        if r.get('is_sent'):
            domain_senders[key]['sent_count'] += 1
        else:
            domain_senders[key]['received_count'] += 1

    entities_created = 0
    entities_updated = 0

    for domain_key, info in domain_senders.items():
        emails = list(info['emails'])
        names = list(info['names'])
        dates = sorted(info['dates'])

        display_name = names[0] if names else domain_key
        for n in names:
            if not any(x in n.lower() for x in ['noreply', 'no-reply', 'donotreply', 'mailer']):
                display_name = n
                break

        relationship_type = 'unknown'
        confidence = 0.5
        try:
            sample_emails = emails[:5]
            sample_names = names[:3]
            classify_prompt = f"Domain: {domain_key}\nEmails: {sample_emails}\nNames: {sample_names}"

            resp = client.messages.create(
                model=AGENT_MODEL,
                max_tokens=100,
                system=CLASSIFY_SYSTEM,
                messages=[{'role': 'user', 'content': classify_prompt}],
            )
            raw = resp.content[0].text.strip()
            if raw.startswith('```'):
                raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()
            result = json.loads(raw)
            display_name = result.get('entity_name', display_name)
            relationship_type = result.get('relationship_type', 'unknown')
            confidence = result.get('confidence', 0.5)
        except Exception:
            pass

        first_contact = dates[0] if dates else None
        last_contact = dates[-1] if dates else None
        interaction_count = info['sent_count'] + info['received_count']
        engagement_score = min(1.0, info['sent_count'] / max(interaction_count, 1) * 2)

        try:
            res = sb.table('entities').upsert({
                'user_id': user_id,
                'type': 'person' if _is_personal_email(_extract_domain(emails[0])) else 'company',
                'name': display_name,
                'properties': {'confidence': confidence},
                'source': 'gmail_deep_scan',
                'relationship_type': relationship_type,
                'email_domains': list({_extract_domain(e) for e in emails}),
                'first_contact': first_contact,
                'last_contact': last_contact,
                'interaction_count': interaction_count,
                'engagement_score': engagement_score,
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }, on_conflict='user_id,type,name').execute()

            if res.data:
                entities_created += 1
            else:
                entities_updated += 1
        except Exception:
            pass

    try:
        sb.table('email_scan_status').update({
            'status': 'detecting_subscriptions',
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }).eq('user_id', user_id).execute()
    except Exception:
        pass

    return {
        'user_id': user_id,
        'domains_processed': len(domain_senders),
        'entities_created': entities_created,
        'entities_updated': entities_updated,
    }
