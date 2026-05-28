# services/agents/email_intelligence/agentic_pipeline.py
"""
Agentic Email Knowledge Graph Builder.

A unified pipeline that reasons like a detective:
1. THREAD RECONSTRUCTION: Group emails by thread, reference number, and temporal proximity
2. ENTITY GRAPH BUILDING: Build entity relationships from evidence
3. RELATIONSHIP INFERENCE: Find cross-entity connections (escalation, delegation, same-case)
4. SITUATION DETECTION: Zero-shot case discovery from entity clusters with full context

This is the ONLY pipeline needed. It replaces case_discoverer.py and pattern_scanner.py
for the core case detection logic.
"""
import os
import re
import json
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from supabase import create_client
from llm import get_client, BRIEF_MODEL, AGENT_MODEL

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


# ─── Step 1: Thread Reconstruction ───────────────────────────────────────────

def _extract_references(text: str) -> set:
    """Extract all reference numbers, case numbers, order IDs from email text."""
    patterns = [
        r'\b([A-Z]{1,4}[-/]\d{4,15})\b',              # DE-12345, AZ-123456789
        r'\baktenzeichen[:\s]+([A-Z0-9\-\.\/\s]{4,25})',  # Aktenzeichen: 5284-26-02-0189 (with spaces)
        r'\b(\d{4}[-\s]\d{2}[-\s]\d{2}[-\s]\d{4}[-\s]\d)',  # 5284-26-02-0189-0 or 5284 26 02 0189 0
        r'\bvorgangs?(?:nummer)?[:\s#]+([A-Z0-9\-]{6,15})',   # Vorgangsnummer: 0023262811
        r'\bkunden(?:nummer)?[:\s]+(\d{7,12})',         # Kundennummer: 2216848686
        r'\border[:\s#]+(\d{8,15})',                    # Order: 558972690008
        r'\b(24V\d{8})\b',                              # 24V15535046 (Deutsche Bahn claim)
        r'\b([A-Z]{2,4}\d{8,12})\b',                   # Generic alphanumeric IDs
        r'\bauftrag[:\s#]+([A-Z0-9\-]{6,20})',          # Auftragsnummer
        r'\bfall[:\s#]+([A-Z0-9\-]{4,15})',             # Fallnummer
    ]
    refs = set()
    for p in patterns:
        for m in re.finditer(p, text, re.IGNORECASE):
            ref = re.sub(r'\s+', '-', m.group(1).strip().upper())
            if len(ref) >= 4 and len(ref) <= 30:
                refs.add(ref)
    return refs


def _temporal_cluster(emails: list, window_days: int = 90) -> list[list]:
    """Group emails into temporal clusters (burst of activity = related)."""
    if not emails:
        return []

    sorted_emails = sorted(emails, key=lambda x: x.get('date', ''))
    clusters = [[sorted_emails[0]]]

    for email in sorted_emails[1:]:
        try:
            curr_date = datetime.fromisoformat(email['date'].replace('Z', '+00:00'))
            last_date = datetime.fromisoformat(clusters[-1][-1]['date'].replace('Z', '+00:00'))
            if abs((curr_date - last_date).days) <= window_days:
                clusters[-1].append(email)
            else:
                clusters.append([email])
        except Exception:
            clusters[-1].append(email)

    return clusters


# ─── Step 2: Entity Graph Building ───────────────────────────────────────────

async def build_email_entity_graph(user_id: str) -> dict:
    """
    Build a complete entity graph from email_raw.
    Returns: {
      'entities': {domain: {name, type, emails, refs, first_seen, last_seen}},
      'ref_to_domains': {ref_number: [list of domains mentioning it]},
      'temporal_adjacency': [(domain1, domain2, days_between, ref_shared)]
    }
    """
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # Fetch ALL emails with pagination (Supabase default limit is 1000 rows)
    all_email_data = []
    page_size = 1000
    offset = 0
    while True:
        page = sb.table('email_raw').select(
            'id, from_email, subject, body_text, snippet, date, is_sent, thread_id'
        ).eq('user_id', user_id).order('date').range(offset, offset + page_size - 1).execute()
        if not page.data:
            break
        all_email_data.extend(page.data)
        if len(page.data) < page_size:
            break
        offset += page_size

    class _Wrapper:
        data = all_email_data
    emails = _Wrapper()

    if not emails.data:
        return {'entities': {}, 'ref_to_domains': {}, 'temporal_adjacency': []}

    # Build domain → emails map
    domain_emails = defaultdict(list)
    for email in emails.data:
        from_email = email.get('from_email', '')
        if '@' in from_email:
            domain = from_email.split('@')[1].lower()
        else:
            domain = from_email.lower()

        # Extract references from this email
        text = (email.get('subject') or '') + ' ' + (email.get('body_text') or '') + ' ' + (email.get('snippet') or '')
        refs = _extract_references(text)

        domain_emails[domain].append({
            'id': email['id'],
            'subject': email.get('subject', ''),
            'date': email.get('date', ''),
            'is_sent': email.get('is_sent', False),
            'refs': refs,
            'snippet': (email.get('body_text') or email.get('snippet') or '')[:300],
        })

    # Build ref → domains map (which domains share the same reference number)
    ref_to_domains = defaultdict(set)
    for domain, domain_mail_list in domain_emails.items():
        for email in domain_mail_list:
            for ref in email.get('refs', set()):
                ref_to_domains[ref].add(domain)

    # Find temporal adjacency (domain A stops → domain B starts within 90 days)
    temporal_adjacency = []
    domains = list(domain_emails.keys())

    for i, d1 in enumerate(domains):
        mails1 = sorted(domain_emails[d1], key=lambda x: x['date'])
        last_d1 = mails1[-1]['date'] if mails1 else None
        refs_d1 = set().union(*[m.get('refs', set()) for m in mails1])

        if not last_d1:
            continue

        try:
            last_d1_dt = datetime.fromisoformat(last_d1.replace('Z', '+00:00'))
        except Exception:
            continue

        for d2 in domains[i+1:]:
            mails2 = sorted(domain_emails[d2], key=lambda x: x['date'])
            first_d2 = mails2[0]['date'] if mails2 else None
            refs_d2 = set().union(*[m.get('refs', set()) for m in mails2])

            if not first_d2:
                continue

            try:
                first_d2_dt = datetime.fromisoformat(first_d2.replace('Z', '+00:00'))
            except Exception:
                continue

            days_between = (first_d2_dt - last_d1_dt).days
            shared_refs = refs_d1 & refs_d2

            # Adjacent in time (d1 ends, d2 starts within 180 days) OR shared references
            if (0 <= days_between <= 180) or shared_refs:
                temporal_adjacency.append({
                    'domain_1': d1,
                    'domain_2': d2,
                    'days_between': days_between,
                    'shared_refs': list(shared_refs),
                    'relationship_strength': len(shared_refs) * 3 + (1 if 0 <= days_between <= 90 else 0),
                })

    return {
        'entities': {d: {
            'domain': d,
            'email_count': len(mails),
            'sent_count': sum(1 for m in mails if m.get('is_sent')),
            'refs': list(set().union(*[m.get('refs', set()) for m in mails]))[:10],
            'first_seen': min((m['date'] for m in mails), default=''),
            'last_seen': max((m['date'] for m in mails), default=''),
            'sample_subjects': [m['subject'][:60] for m in sorted(mails, key=lambda x: x['date'], reverse=True)[:5]],
        } for d, mails in domain_emails.items()},
        'ref_to_domains': {ref: list(domains) for ref, domains in ref_to_domains.items() if len(domains) >= 2},
        'temporal_adjacency': sorted(temporal_adjacency, key=lambda x: x['relationship_strength'], reverse=True)[:50],
    }


# ─── Step 3: Relationship Inference ──────────────────────────────────────────

RELATIONSHIP_INFERENCE_PROMPT = """You are analyzing email metadata to find RELATED entities (companies/organizations).

Given temporal adjacency data (when did each organization email this person), identify which organizations are likely part of the SAME SITUATION.

Patterns that indicate same situation:
1. ESCALATION: Organization A emails stop, then Organization B (possibly a debt collector/law firm) starts emailing with the same reference number
2. DELEGATION: Organization A refers to same case number as Organization B
3. HANDOVER: Organizational transition (gym → debt collector, bank → debt collection agency)
4. SAME COMPANY DIFFERENT DOMAIN: noreply@company.de + service@company.de + billing@company.de

German-specific escalation patterns:
- "Inkasso", "Mahnbescheid", "Forderung", "einfach-klaeren", "kohlkg", "creditreform" = debt collectors
- If a service provider domain appears then a domain with these words appears within 180 days = escalation case

Data:
{adjacency_data}

Reference numbers shared between domains:
{shared_refs}

Return JSON array of relationship groups:
[
  {{
    "domains": ["domain1.de", "domain2.de"],
    "relationship": "escalation|same_company|delegation|unknown",
    "situation_hint": "Brief description of the likely situation",
    "confidence": 0.0-1.0
  }}
]

Return ONLY valid JSON array. Empty array [] if no clear relationships found."""


async def infer_entity_relationships(entity_graph: dict) -> list[dict]:
    """
    Use Sonnet to reason about which entities are part of the same situation.
    Returns list of relationship groups.
    """
    adjacency = entity_graph.get('temporal_adjacency', [])
    shared_refs = entity_graph.get('ref_to_domains', {})

    if not adjacency and not shared_refs:
        return []

    # Prepare compact representation for Sonnet
    adj_lines = []
    for adj in adjacency[:30]:
        d1_info = entity_graph['entities'].get(adj['domain_1'], {})
        d2_info = entity_graph['entities'].get(adj['domain_2'], {})
        line = f"{adj['domain_1']} (last email: {d1_info.get('last_seen','?')[:10]}) → {adj['domain_2']} (first email: {d2_info.get('first_seen','?')[:10]}, days_between={adj['days_between']})"
        if adj.get('shared_refs'):
            line += f" [SHARED REFS: {adj['shared_refs'][:3]}]"
        adj_lines.append(line)

    ref_lines = [f"{ref}: {', '.join(domains)}" for ref, domains in list(shared_refs.items())[:20]]

    prompt = RELATIONSHIP_INFERENCE_PROMPT.format(
        adjacency_data='\n'.join(adj_lines) if adj_lines else 'None',
        shared_refs='\n'.join(ref_lines) if ref_lines else 'None',
    )

    client = get_client()
    try:
        response = client.messages.create(
            model=BRIEF_MODEL,
            max_tokens=1000,
            messages=[{'role': 'user', 'content': prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        return json.loads(raw)
    except Exception:
        return []


# ─── Step 4: Situation Detection ─────────────────────────────────────────────

SITUATION_DETECTION_PROMPT = """You are Chief, analyzing a CLUSTER of related emails to identify if there is an active SITUATION requiring attention.

Entity cluster (related organizations):
{entity_info}

Email evidence (most recent emails from these entities):
{email_evidence}

Reference numbers linking these entities: {shared_refs}

Determine if this cluster represents an active SITUATION. A situation is:
- A dispute or disagreement requiring resolution
- An incomplete process (account setup stalled, application pending)
- A financial issue (unpaid bill, subscription problem)
- A legal or administrative matter requiring action

If this IS a situation, return JSON:
{{
  "is_situation": true,
  "title": "Brief title (max 60 chars)",
  "status": "open|progressing|stalled|needs_action|resolved",
  "priority": "low|normal|high|critical",
  "category": "dispute|account_setup|application|billing|legal|housing|travel|other",
  "summary": "2-3 sentence summary",
  "pending_action": "What the user needs to do next (null if nothing)",
  "stalled_since": "ISO date if stalled (null otherwise)",
  "confidence": 0.0-1.0,
  "timeline": [{{"date": "YYYY-MM-DD", "event": "description", "direction": "sent|received"}}],
  "involved_domains": ["domain1", "domain2"]
}}

Priority:
- critical: Active legal threat, debt collection, imminent financial harm, housing risk
- high: Stalled important process, unresolved dispute, significant pending decision
- normal: Active correspondence, pending application
- low: Routine or likely resolved

If NOT a situation: {{"is_situation": false}}

Return ONLY valid JSON."""


async def detect_situation_from_cluster(
    user_id: str,
    entity_cluster: list[str],
    entity_graph: dict,
) -> dict | None:
    """
    Run Sonnet on a cluster of related entities to detect a situation.
    """
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # Gather all emails from cluster entities
    all_emails = []
    for domain in entity_cluster[:5]:
        emails = sb.table('email_raw').select(
            'subject, body_text, snippet, date, is_sent, from_email'
        ).eq('user_id', user_id).ilike('from_email', f'%{domain}%') \
         .order('date', desc=True).limit(15).execute()

        for e in (emails.data or []):
            all_emails.append({
                'date': e.get('date', '')[:10],
                'subject': (e.get('subject') or '')[:80],
                'snippet': (e.get('body_text') or e.get('snippet') or '')[:200],
                'direction': 'SENT' if e.get('is_sent') else 'RECEIVED',
                'from': e.get('from_email', '')[:40],
            })

    all_emails.sort(key=lambda x: x['date'], reverse=True)

    # Build entity info
    entity_info_lines = []
    for domain in entity_cluster:
        info = entity_graph['entities'].get(domain, {})
        entity_info_lines.append(
            f"- {domain}: {info.get('email_count',0)} emails, "
            f"last contact {info.get('last_seen','?')[:10]}, "
            f"refs: {info.get('refs', [])[:3]}"
        )

    # Build email evidence
    evidence_lines = []
    for e in all_emails[:20]:
        evidence_lines.append(f"[{e['date']}] {e['direction']}: {e['subject']}")
        if e.get('snippet'):
            evidence_lines.append(f"  {e['snippet'][:150]}")

    # Find shared refs
    shared_refs = []
    for ref, domains in entity_graph.get('ref_to_domains', {}).items():
        if any(d in domains for d in entity_cluster):
            shared_refs.append(ref)

    prompt = SITUATION_DETECTION_PROMPT.format(
        entity_info='\n'.join(entity_info_lines),
        email_evidence='\n'.join(evidence_lines),
        shared_refs=', '.join(shared_refs[:5]) if shared_refs else 'None found',
    )

    client = get_client()
    try:
        response = client.messages.create(
            model=BRIEF_MODEL,
            max_tokens=1200,
            messages=[{'role': 'user', 'content': prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        return json.loads(raw)
    except Exception:
        return None


# ─── Step 5: Full Pipeline ────────────────────────────────────────────────────

async def run_agentic_pipeline(user_id: str) -> dict:
    """
    THE main pipeline. Replaces all previous case discovery approaches.

    Steps:
    1. Build entity graph from all emails (thread/reference reconstruction)
    2. Infer relationships between entities (who is connected to who)
    3. Detect situations from entity clusters
    4. Save cases to DB

    Zero manual intervention. Zero hardcoded entity names.
    Works for any inbox in any language.
    """
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # Step 1: Build entity graph
    entity_graph = await build_email_entity_graph(user_id)
    entities = entity_graph['entities']

    if not entities:
        return {'user_id': user_id, 'situations_found': 0}

    # Step 2: Infer relationships
    relationships = await infer_entity_relationships(entity_graph)

    # Step 3: Build clusters from relationships
    # Start with related clusters, then add isolated entities with high interaction
    processed_domains = set()
    clusters = []

    # Add relationship-based clusters
    for rel in relationships:
        if rel.get('confidence', 0) >= 0.5:
            cluster_domains = rel.get('domains', [])
            if cluster_domains:
                clusters.append(cluster_domains)
                processed_domains.update(cluster_domains)

    # Add isolated entities that have sent emails (user interacted) or have high volume
    for domain, info in entities.items():
        if domain in processed_domains:
            continue
        # Include if: user sent emails to this domain, OR many emails, OR has reference numbers
        if info.get('sent_count', 0) > 0 or info.get('email_count', 0) > 5 or info.get('refs'):
            clusters.append([domain])

    # Step 4: Detect situations from clusters
    cases_created = 0
    cases_skipped = 0

    for cluster in clusters[:80]:  # Process up to 80 clusters
        result = await detect_situation_from_cluster(user_id, cluster, entity_graph)

        if not result or not result.get('is_situation'):
            cases_skipped += 1
            continue

        confidence = result.get('confidence', 0.5)
        if confidence < 0.45:
            cases_skipped += 1
            continue

        # Check if similar case already exists
        title = result['title'][:200]
        try:
            existing = sb.table('email_cases').select('id').eq('user_id', user_id) \
                .eq('title', title).maybe_single().execute()
            if existing and existing.data:
                continue
        except Exception:
            pass  # If check fails, proceed to insert

        # Save the case
        sb.table('email_cases').insert({
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
            'thread_ids': result.get('involved_domains', []),  # reuse field for domains
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }).execute()
        cases_created += 1

    return {
        'user_id': user_id,
        'entities_analyzed': len(entities),
        'clusters_processed': len(clusters),
        'relationships_found': len(relationships),
        'situations_found': cases_created,
        'situations_skipped': cases_skipped,
    }
