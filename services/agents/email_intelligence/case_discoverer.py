# services/agents/email_intelligence/case_discoverer.py
"""
Case Discovery Engine.
For each active (non-newsletter) entity, fetches all related emails
(sent + received) and uses Sonnet to identify distinct CASES.

A Case is an ongoing situation: a dispute, account setup, job application,
purchase problem, or any active correspondence requiring attention.

Reference cases from Mohamed's inbox:
- FitStar/McFit dispute → debt collector escalation
- Congstar billing issue → potential escalation
- Deutsche Bank / Deutsche Bahn account/ticket issues
- ImmoScout apartment search
- BMW Group / Siemens job applications
"""
import os
import json
from datetime import datetime, timezone, timedelta
from supabase import create_client
from llm import get_client, BRIEF_MODEL, AGENT_MODEL

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

# Sonnet prompt for case identification
CASE_DISCOVERY_SYSTEM = """You analyze email threads between a user and an organization to identify active CASES.

A CASE is an ongoing situation requiring attention: a dispute, account setup, job application,
purchase problem, subscription issue, or any correspondence the user likely needs to act on.

NOT a case:
- Single marketing/newsletter email
- Automated receipts with no follow-up needed
- Login notifications or security alerts

Given a list of emails (sent + received) between the user and ONE organization, identify distinct cases.

Return JSON array of cases. Each case:
{
  "title": "Brief descriptive title (max 60 chars)",
  "status": "open|progressing|stalled|needs_action|resolved",
  "priority": "low|normal|high|critical",
  "category": "dispute|account_setup|application|purchase|service_request|billing|travel|other",
  "pending_action": "What the user needs to do next (null if no action needed)",
  "stalled_since": "ISO date when progress stopped (null if not stalled)",
  "confidence": 0.0-1.0,
  "timeline": [
    {"date": "YYYY-MM-DD", "event": "brief description", "direction": "received|sent"}
  ],
  "summary": "2-3 sentence summary of the situation"
}

Priority rules:
- critical: Legal threat, debt collection, imminent deadline <7 days
- high: Dispute, stalled important account, overdue response >14 days
- normal: Active correspondence, pending application
- low: Resolved or low-stakes

Return ONLY a JSON array. Empty array [] if no cases found. No prose."""


async def discover_cases_for_entity(
    user_id: str,
    entity_id: str,
    entity_name: str,
    relationship_type: str,
    email_domains: list[str],
) -> list[dict]:
    """
    Fetch all emails for one entity and run Sonnet case discovery.
    Returns list of case dicts (not yet saved to DB).
    """
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # Build domain filter — match any email from this entity's domains
    if not email_domains:
        return []

    # Fetch all emails from/to this entity's domains
    all_emails = []
    for domain in email_domains[:5]:  # max 5 domains per entity
        # Received emails
        recv = sb.table('email_raw').select(
            'subject, snippet, body_text, date, is_sent, from_email, to_emails'
        ).eq('user_id', user_id).ilike('from_email', f'%{domain}%') \
         .order('date', desc=False).limit(100).execute()

        all_emails.extend(recv.data or [])

        # Sent emails to this domain
        # We check body/subject since to_emails is an array
        sent = sb.table('email_raw').select(
            'subject, snippet, body_text, date, is_sent, from_email, to_emails'
        ).eq('user_id', user_id).eq('is_sent', True) \
         .order('date', desc=False).limit(50).execute()

        # Filter sent emails that went to this domain
        for e in (sent.data or []):
            to_list = e.get('to_emails', []) or []
            if any(domain in addr.lower() for addr in to_list):
                all_emails.append(e)

    if not all_emails:
        return []

    # Deduplicate by date+subject
    seen = set()
    unique_emails = []
    for e in all_emails:
        key = (e.get('date', '')[:10], e.get('subject', '')[:50])
        if key not in seen:
            seen.add(key)
            unique_emails.append(e)

    unique_emails.sort(key=lambda x: x.get('date', ''))

    # Skip if only automated/transactional emails and not relevant
    if len(unique_emails) == 0:
        return []

    # Build email summary for Sonnet (cap at 50 emails, use snippets)
    email_lines = []
    for e in unique_emails[:50]:
        direction = 'SENT' if e.get('is_sent') else 'RECEIVED'
        date = e.get('date', '')[:10]
        subject = (e.get('subject') or '(no subject)')[:80]
        snippet = (e.get('body_text') or e.get('snippet') or '')[:200]
        email_lines.append(f"[{date}] {direction}: {subject}")
        if snippet:
            email_lines.append(f"  Preview: {snippet[:150]}")

    prompt = f"""Organization: {entity_name} (type: {relationship_type})
Email domains: {email_domains}
Total emails: {len(unique_emails)}

EMAIL THREAD (chronological):
{chr(10).join(email_lines)}

Identify any active cases for this organization."""

    client = get_client()
    try:
        response = client.messages.create(
            model=BRIEF_MODEL,  # Sonnet for quality case reasoning
            max_tokens=1500,
            system=CASE_DISCOVERY_SYSTEM,
            messages=[{'role': 'user', 'content': prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()

        cases = json.loads(raw)
        if not isinstance(cases, list):
            return []

        # Attach entity reference to each case
        for c in cases:
            c['_entity_id'] = entity_id
            c['_entity_name'] = entity_name
            c['_email_count'] = len(unique_emails)

        return cases

    except (json.JSONDecodeError, Exception):
        return []


async def run_case_discovery(user_id: str) -> dict:
    """
    Run case discovery for all active non-newsletter entities.
    Saves discovered cases to email_cases table.
    Returns summary of what was found.
    """
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # Get all non-newsletter entities for this user
    skip_types = ('newsletter',)
    entities = sb.table('entities').select(
        'id, name, relationship_type, email_domains, interaction_count'
    ).eq('user_id', user_id) \
     .not_.is_('relationship_type', 'null') \
     .gt('interaction_count', 1) \
     .execute()

    if not entities.data:
        return {'user_id': user_id, 'entities_analyzed': 0, 'cases_found': 0}

    cases_found = 0
    entities_analyzed = 0
    errors = 0

    # Update scan status
    try:
        sb.table('email_scan_status').update({
            'status': 'scanning',
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }).eq('user_id', user_id).execute()
    except Exception:
        pass

    for entity in entities.data:
        rtype = entity.get('relationship_type', '')
        if rtype in skip_types:
            continue

        # Skip entities with no email domains
        domains = entity.get('email_domains') or []
        if not domains:
            continue

        entities_analyzed += 1

        try:
            cases = await discover_cases_for_entity(
                user_id=user_id,
                entity_id=entity['id'],
                entity_name=entity['name'],
                relationship_type=rtype,
                email_domains=domains,
            )

            for case_data in cases:
                confidence = case_data.get('confidence', 0.5)
                if confidence < 0.4:
                    continue  # Skip low-confidence cases

                # Check if case already exists (by title + entity)
                existing = sb.table('email_cases').select('id').eq('user_id', user_id) \
                    .eq('title', case_data['title'][:200]).maybe_single().execute()

                if existing.data:
                    # Update existing case
                    sb.table('email_cases').update({
                        'status': case_data.get('status', 'open'),
                        'priority': case_data.get('priority', 'normal'),
                        'summary': case_data.get('summary'),
                        'pending_action': case_data.get('pending_action'),
                        'stalled_since': case_data.get('stalled_since'),
                        'timeline': case_data.get('timeline', []),
                        'confidence': confidence,
                        'entities': [case_data['_entity_id']],
                        'updated_at': datetime.now(timezone.utc).isoformat(),
                    }).eq('id', existing.data['id']).execute()
                else:
                    # Insert new case
                    sb.table('email_cases').insert({
                        'user_id': user_id,
                        'title': case_data['title'][:200],
                        'status': case_data.get('status', 'open'),
                        'priority': case_data.get('priority', 'normal'),
                        'category': case_data.get('category'),
                        'summary': case_data.get('summary'),
                        'pending_action': case_data.get('pending_action'),
                        'stalled_since': case_data.get('stalled_since'),
                        'timeline': case_data.get('timeline', []),
                        'confidence': confidence,
                        'entities': [case_data['_entity_id']],
                        'created_at': datetime.now(timezone.utc).isoformat(),
                        'updated_at': datetime.now(timezone.utc).isoformat(),
                    }).execute()
                    cases_found += 1

        except Exception:
            errors += 1

    # Mark complete
    try:
        sb.table('email_scan_status').update({
            'status': 'complete',
            'completed_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }).eq('user_id', user_id).execute()
    except Exception:
        pass

    return {
        'user_id': user_id,
        'entities_analyzed': entities_analyzed,
        'cases_found': cases_found,
        'errors': errors,
    }
