# services/agents/email_intelligence/cross_entity_reasoner.py
"""
Cross-Entity Reasoner.
Detects when separate entities are actually part of the SAME situation.

Key patterns to detect:
1. ESCALATION: Company A emails stop → Collection agency B emails start
   Example: FitStar (service_provider) + debt collector = same dispute
2. STALLED APPLICATION: Bank emails + user's sent email + silence = stalled setup
   Example: Deutsche Bank account creation with no login details arriving
3. REFERENCE NUMBER MATCH: Two entities mention same Ref#, amount, or order ID
4. TEMPORAL PROXIMITY: Two entities start emailing within 30 days of each other
   about related topics

When a cross-entity link is found, the two cases are MERGED into one master case.
"""
import os
import json
import re
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from supabase import create_client
from llm import get_client, BRIEF_MODEL

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

# Patterns indicating debt collection / escalation
DEBT_COLLECTOR_SIGNALS = [
    r'inkasso', r'mahnbescheid', r'mahnung', r'forderung', r'schulden',
    r'vollstreckung', r'inkassobuero', r'debt\s+collect', r'collection\s+agency',
    r'zahlungsaufforderung', r'letzte\s+mahnung', r'ausstehend',
]

# Reference number patterns
REF_PATTERNS = [
    r'(?:ref|reference|auftrag|vorgang|kundennummer|kunden-nr|aktenzeichen)[:\s#.]*([A-Z0-9\-]{4,20})',
    r'(?:order|bestell)[:\s#.]*([A-Z0-9\-]{4,20})',
    r'(?:rechnungs|invoice)[:\s#.]*([A-Z0-9\-]{4,20})',
    r'([A-Z]{2,4}[-/]\d{4,12})',  # Generic ref like DE-12345678
]


def _extract_ref_numbers(text: str) -> set[str]:
    """Extract reference/order numbers from email text."""
    refs = set()
    text_lower = text.lower()
    for pattern in REF_PATTERNS:
        for match in re.finditer(pattern, text_lower, re.IGNORECASE):
            ref = match.group(1).upper().strip()
            if len(ref) >= 4:
                refs.add(ref)
    return refs


def _has_debt_signals(text: str) -> bool:
    """Check if text contains debt collection signals."""
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in DEBT_COLLECTOR_SIGNALS)


async def find_escalation_pairs(user_id: str) -> list[dict]:
    """
    Find entity pairs where a service_provider's emails stop and
    a debt_collector starts emailing — classic dispute escalation.
    Returns list of {source_case_id, target_case_id, pattern, confidence}
    """
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # Get all cases with their entity types
    cases = sb.table('email_cases').select('id, title, status, entities, timeline, summary') \
        .eq('user_id', user_id) \
        .not_.is_('entities', '{}') \
        .execute()

    if not cases.data or len(cases.data) < 2:
        return []

    # Get entity types for all case entities
    entity_ids = []
    for case in cases.data:
        entity_ids.extend(case.get('entities', []))

    entity_ids = list(set(entity_ids))
    if not entity_ids:
        return []

    entities_data = sb.table('entities').select('id, name, relationship_type, email_domains, last_contact') \
        .in_('id', entity_ids[:50]).execute()

    entity_map = {e['id']: e for e in (entities_data.data or [])}

    # Find cases with debt_collector entities
    debt_cases = []
    service_cases = []

    for case in cases.data:
        for eid in (case.get('entities') or []):
            ent = entity_map.get(eid, {})
            rtype = ent.get('relationship_type', '')
            if rtype == 'debt_collector':
                debt_cases.append({'case': case, 'entity': ent})
            elif rtype in ('service_provider', 'bank', 'marketplace'):
                service_cases.append({'case': case, 'entity': ent})

    pairs = []

    # For each debt collector case, find service provider cases that ended before it started
    for dc in debt_cases:
        dc_timeline = dc['case'].get('timeline', [])
        if not dc_timeline:
            continue

        dc_first_date_str = dc_timeline[0].get('date', '') if dc_timeline else ''
        try:
            dc_first_date = datetime.fromisoformat(dc_first_date_str)
        except Exception:
            continue

        # Look for service provider cases that ended within 180 days before debt collector started
        window_start = dc_first_date - timedelta(days=180)

        for sc in service_cases:
            sc_timeline = sc['case'].get('timeline', [])
            if not sc_timeline:
                continue

            sc_last_date_str = sc_timeline[-1].get('date', '') if sc_timeline else ''
            try:
                sc_last_date = datetime.fromisoformat(sc_last_date_str)
            except Exception:
                continue

            # Service case ended before debt collection started — possible escalation
            if window_start <= sc_last_date <= dc_first_date:
                confidence = 0.65

                # Check name/keyword overlap for higher confidence
                dc_summary = (dc['case'].get('summary') or '').lower()
                sc_summary = (sc['case'].get('summary') or '').lower()
                dc_title = (dc['case'].get('title') or '').lower()
                sc_title = (sc['case'].get('title') or '').lower()

                # Look for shared amounts (€XX.XX patterns)
                amounts_re = r'€?\d+[,.]?\d*\s*(?:euro|eur)?'
                dc_amounts = set(re.findall(amounts_re, dc_summary + dc_title))
                sc_amounts = set(re.findall(amounts_re, sc_summary + sc_title))
                if dc_amounts & sc_amounts:
                    confidence = 0.85

                pairs.append({
                    'source_case_id': sc['case']['id'],
                    'target_case_id': dc['case']['id'],
                    'source_title': sc['case']['title'],
                    'target_title': dc['case']['title'],
                    'source_entity': sc['entity']['name'],
                    'target_entity': dc['entity']['name'],
                    'pattern': 'escalation',
                    'confidence': confidence,
                    'description': f"{sc['entity']['name']} dispute escalated to {dc['entity']['name']}",
                })

    return pairs


async def find_reference_matches(user_id: str) -> list[dict]:
    """
    Find cases where the same reference number appears in emails from different entities.
    """
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # Get emails with body text, grouped by entity domains
    emails = sb.table('email_raw').select(
        'id, subject, body_text, snippet, from_email, date'
    ).eq('user_id', user_id) \
     .not_.is_('body_text', 'null') \
     .limit(5000).execute()

    if not emails.data:
        return []

    # Extract ref numbers per domain
    domain_refs: dict[str, set] = defaultdict(set)
    for email in emails.data:
        domain = email.get('from_email', '').split('@')[-1].lower() if '@' in email.get('from_email', '') else ''
        if not domain:
            continue
        text = (email.get('body_text') or '') + ' ' + (email.get('subject') or '')
        refs = _extract_ref_numbers(text)
        domain_refs[domain].update(refs)

    # Find domains that share reference numbers
    pairs = []
    domains = list(domain_refs.keys())
    for i, d1 in enumerate(domains):
        for d2 in domains[i+1:]:
            shared = domain_refs[d1] & domain_refs[d2]
            if shared:
                pairs.append({
                    'domain_1': d1,
                    'domain_2': d2,
                    'shared_refs': list(shared)[:3],
                    'pattern': 'reference_match',
                    'confidence': 0.8 if len(shared) >= 2 else 0.6,
                })

    return pairs


async def merge_linked_cases(user_id: str, case_id_1: str, case_id_2: str, reason: str) -> str:
    """
    Merge two cases into one master case.
    The higher-priority case becomes the master; lower-priority is marked resolved and linked.
    Returns the master case ID.
    """
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    c1 = sb.table('email_cases').select('*').eq('id', case_id_1).maybe_single().execute()
    c2 = sb.table('email_cases').select('*').eq('id', case_id_2).maybe_single().execute()

    if not c1.data or not c2.data:
        return case_id_1

    PRIORITY_ORDER = {'critical': 4, 'high': 3, 'normal': 2, 'low': 1}
    p1 = PRIORITY_ORDER.get(c1.data.get('priority', 'normal'), 2)
    p2 = PRIORITY_ORDER.get(c2.data.get('priority', 'normal'), 2)

    master = c1.data if p1 >= p2 else c2.data
    secondary = c2.data if p1 >= p2 else c1.data

    # Merge timelines
    tl1 = master.get('timeline', []) or []
    tl2 = secondary.get('timeline', []) or []
    merged_timeline = sorted(tl1 + tl2, key=lambda x: x.get('date', ''))

    # Merge entities
    entities = list(set((master.get('entities') or []) + (secondary.get('entities') or [])))

    # Update master
    sb.table('email_cases').update({
        'timeline': merged_timeline,
        'entities': entities,
        'summary': f"{master.get('summary', '')} [MERGED: {reason}]",
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }).eq('id', master['id']).execute()

    # Mark secondary as resolved + linked
    sb.table('email_cases').update({
        'status': 'resolved',
        'user_notes': f"Merged into case {master['id']}: {reason}",
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }).eq('id', secondary['id']).execute()

    return master['id']


async def run_cross_entity_reasoning(user_id: str) -> dict:
    """
    Run all cross-entity reasoning patterns and merge linked cases.
    """
    escalation_pairs = await find_escalation_pairs(user_id)
    ref_pairs = await find_reference_matches(user_id)

    merges_done = 0
    links_found = len(escalation_pairs) + len(ref_pairs)

    # Auto-merge high-confidence escalation pairs
    for pair in escalation_pairs:
        if pair['confidence'] >= 0.75:
            await merge_linked_cases(
                user_id,
                pair['source_case_id'],
                pair['target_case_id'],
                pair['description'],
            )
            merges_done += 1

    return {
        'user_id': user_id,
        'links_found': links_found,
        'escalation_pairs': len(escalation_pairs),
        'reference_matches': len(ref_pairs),
        'auto_merges': merges_done,
        'escalations': [
            {'src': p['source_title'][:50], 'tgt': p['target_title'][:50], 'conf': p['confidence']}
            for p in escalation_pairs
        ],
    }
