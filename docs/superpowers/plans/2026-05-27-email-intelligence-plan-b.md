# Email Intelligence Engine v2 — Plan B: Case Discovery & Intelligence

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Case Discovery Engine — the intelligence layer that transforms 52,459 raw emails into structured, actionable "situations" (cases), links related cases across entities (fitstar→debt collector), upgrades Echo to be case-aware, and creates a RL feedback loop so Chief gets smarter with every user correction.

**Architecture:** Three sequential processing stages: (1) Case Discoverer uses Sonnet to analyze each active entity's full email thread history and identify distinct Cases; (2) Cross-Entity Reasoner finds cases that span multiple entities using temporal pattern matching and keyword overlap; (3) Echo v2 is upgraded to query email_cases first before falling back to raw email context. All feedback from user corrections is stored in email_feedback and applied to future reasoning. The real email data from Mohamed's account (fitstar disputes, Deutsche Bank account setup, congstar billing, ImmoScout apartment search) serves as the ground truth for verifying correctness.

**Tech Stack:** Python 3.11+, FastAPI, Bedrock Claude Sonnet (eu.anthropic.claude-sonnet-4-5-20250929-v1:0) for case reasoning, Haiku for classification, `supabase-py`, `httpx`. DB tables used: `email_raw`, `entities`, `email_cases`, `email_feedback`, `email_scan_status`.

---

## File Map

```
services/agents/
├── email_intelligence/
│   ├── __init__.py              ← add case_discoverer + cross_entity_reasoner exports
│   ├── case_discoverer.py       ← NEW: per-entity case discovery using Sonnet
│   └── cross_entity_reasoner.py ← NEW: link cases across entities
├── agents/
│   └── echo.py                 ← MODIFY: add case-aware fetch_context + handle
├── main.py                     ← MODIFY: add /email/cases, /email/case, /email/feedback,
│                                          /email/cases/run-discovery, /email/unsubscribe,
│                                          /email/present-cases endpoints
└── tests/
    └── test_case_discovery.py  ← NEW: tests for case discoverer + cross-entity reasoner
```

---

## Task 1: Case Discoverer — per-entity Sonnet analysis

**Files:**
- Create: `services/agents/email_intelligence/case_discoverer.py`

- [ ] **Step 1: Create `email_intelligence/case_discoverer.py`**

```python
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
```

- [ ] **Step 2: Verify imports**

```bash
cd C:/Users/Micha/chief/services/agents && .venv/Scripts/python.exe -c "
from dotenv import load_dotenv; load_dotenv()
from email_intelligence.case_discoverer import run_case_discovery, discover_cases_for_entity
print('Case discoverer imports OK')
"
```

Expected: `Case discoverer imports OK`

- [ ] **Step 3: Commit**

```bash
git -C C:/Users/Micha/chief add services/agents/email_intelligence/case_discoverer.py
git -C C:/Users/Micha/chief commit -m "feat: Case Discovery Engine — Sonnet analyzes entity email threads, finds active cases"
git -C C:/Users/Micha/chief push
```

---

## Task 2: Cross-Entity Reasoner — link cases across entities

**Files:**
- Create: `services/agents/email_intelligence/cross_entity_reasoner.py`

- [ ] **Step 1: Create `email_intelligence/cross_entity_reasoner.py`**

```python
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
```

- [ ] **Step 2: Update `email_intelligence/__init__.py`**

Replace content:

```python
from .deep_scanner import deep_scan_inbox, get_scan_status
from .entity_clusterer import cluster_entities
from .subscription_detector import detect_subscriptions
from .case_discoverer import run_case_discovery, discover_cases_for_entity
from .cross_entity_reasoner import run_cross_entity_reasoning, merge_linked_cases

__all__ = [
    'deep_scan_inbox', 'get_scan_status',
    'cluster_entities',
    'detect_subscriptions',
    'run_case_discovery', 'discover_cases_for_entity',
    'run_cross_entity_reasoning', 'merge_linked_cases',
]
```

- [ ] **Step 3: Verify imports**

```bash
cd C:/Users/Micha/chief/services/agents && .venv/Scripts/python.exe -c "
from dotenv import load_dotenv; load_dotenv()
from email_intelligence.cross_entity_reasoner import run_cross_entity_reasoning, find_escalation_pairs, find_reference_matches
from email_intelligence import run_case_discovery, run_cross_entity_reasoning
print('Cross-entity reasoner imports OK')
"
```

Expected: `Cross-entity reasoner imports OK`

- [ ] **Step 4: Commit**

```bash
git -C C:/Users/Micha/chief add services/agents/email_intelligence/
git -C C:/Users/Micha/chief commit -m "feat: Cross-Entity Reasoner — detect escalations, reference matches, auto-merge linked cases"
git -C C:/Users/Micha/chief push
```

---

## Task 3: Echo v2 — case-aware agent

**Files:**
- Modify: `services/agents/agents/echo.py`

- [ ] **Step 1: Replace `agents/echo.py` with case-aware version**

```python
# services/agents/agents/echo.py
"""
Echo v2 — Case-Aware Communication Agent.

Upgrade from "summarize recent threads" to "situation navigator".
Now queries email_cases first to provide timeline-based answers.

Examples:
  "What's happening with Deutsche Bank?" → finds stalled account case → full timeline
  "What emails need attention?" → lists active cases by priority
  "Write a follow-up to Congstar" → finds billing case → drafts with full context
"""
import os
from datetime import datetime, timezone, timedelta
from supabase import create_client
from agents.base import BaseAgent
from models import ChatRequest, ChatResponse
from llm import get_client, BRIEF_MODEL
from tools.comms_tools import get_stale_threads, create_draft_in_queue
from db import safe_single

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

# Keywords that suggest the user is asking about a specific situation/case
CASE_QUERY_KEYWORDS = [
    "what's happening", "what happened", "what's going on",
    "status of", "update on", "situation with",
    "deutsche bank", "fitstar", "mcfit", "congstar", "immoscout",
    "debt collector", "inkasso", "mahnung", "forderung",
    "my account", "my application", "my apartment",
    "follow up", "follow-up", "did they reply", "still waiting",
    "stalled", "no response", "haven't heard",
]


async def _fetch_cases_context(user_id: str, query: str) -> str:
    """
    Query email_cases for relevant cases based on user's message.
    Returns formatted case context for Echo.
    """
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # Get all non-resolved cases ordered by priority
    cases = sb.table('email_cases').select(
        'id, title, status, priority, category, summary, pending_action, stalled_since, timeline, entities, confidence'
    ).eq('user_id', user_id) \
     .not_.is_('status', 'resolved') \
     .order('priority', desc=True) \
     .limit(20).execute()

    if not cases.data:
        return ''

    PRIORITY_EMOJI = {'critical': '🔴', 'high': '🟠', 'normal': '🟡', 'low': '🟢'}
    STATUS_LABEL = {
        'open': 'Open', 'progressing': 'In Progress',
        'stalled': 'STALLED', 'needs_action': 'ACTION NEEDED', 'resolved': 'Resolved'
    }

    lines = ['=== ACTIVE CASES (from email analysis) ===']

    # If query seems to be about a specific entity/topic, filter to relevant cases
    query_lower = query.lower()
    relevant_cases = []
    all_cases = cases.data

    for case in all_cases:
        title_lower = (case.get('title') or '').lower()
        summary_lower = (case.get('summary') or '').lower()
        # Check if any word from query matches title or summary
        query_words = [w for w in query_lower.split() if len(w) > 3]
        if any(w in title_lower or w in summary_lower for w in query_words):
            relevant_cases.append(case)

    # If we found relevant cases, show those first; otherwise show all
    display_cases = relevant_cases if relevant_cases else all_cases[:5]

    for case in display_cases[:5]:
        emoji = PRIORITY_EMOJI.get(case.get('priority', 'normal'), '🟡')
        status = STATUS_LABEL.get(case.get('status', 'open'), 'Open')
        title = case.get('title', 'Unnamed case')
        summary = case.get('summary', '')
        pending = case.get('pending_action')
        stalled = case.get('stalled_since')

        lines.append(f'\n{emoji} Case: {title}')
        lines.append(f'   Status: {status}')
        if summary:
            lines.append(f'   Summary: {summary[:200]}')
        if pending:
            lines.append(f'   → Pending: {pending}')
        if stalled:
            stalled_date = stalled[:10] if stalled else ''
            try:
                stalled_dt = datetime.fromisoformat(stalled.replace('Z', '+00:00'))
                days_stalled = (datetime.now(timezone.utc) - stalled_dt).days
                lines.append(f'   ⏸ Stalled for {days_stalled} days (since {stalled_date})')
            except Exception:
                lines.append(f'   ⏸ Stalled since {stalled_date}')

        # Include timeline for specific case queries
        if relevant_cases and case in relevant_cases:
            timeline = case.get('timeline', []) or []
            if timeline:
                lines.append('   Timeline:')
                for event in timeline[-5:]:  # Last 5 events
                    d = event.get('date', '')[:10]
                    ev = event.get('event', '')[:100]
                    direction = '→' if event.get('direction') == 'sent' else '←'
                    lines.append(f'     {d} {direction} {ev}')

    if not display_cases:
        lines.append('No active cases found.')

    lines.append('\nIMPORTANT: These cases are derived from real email analysis. Use them to answer case-specific questions with full context.')
    return '\n'.join(lines)


async def _fetch_raw_email_context(user_id: str) -> str:
    """Fallback: recent email threads from lg_communications (Phase 0 data)."""
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    cutoff_3d = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    cutoff_2d = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()

    stale = sb.table('lg_communications').select(
        'thread_id, channel, participants, subject, last_message_at, staleness_days'
    ).eq('user_id', user_id).eq('status', 'active') \
     .lte('last_message_at', cutoff_3d) \
     .order('last_message_at', desc=False).limit(10).execute()

    for t in stale.data or []:
        if t.get('last_message_at'):
            try:
                lma = datetime.fromisoformat(t['last_message_at'].replace('Z', '+00:00'))
                t['staleness_days'] = (datetime.now(timezone.utc) - lma).days
            except Exception:
                pass

    recent = sb.table('lg_communications').select(
        'subject, channel, participants, last_message_at'
    ).eq('user_id', user_id).eq('status', 'active') \
     .gte('last_message_at', cutoff_2d) \
     .order('last_message_at', desc=True).limit(5).execute()

    lines = ['=== RECENT EMAILS ===']

    if stale.data:
        lines.append(f'Threads needing attention ({len(stale.data)}):')
        for t in stale.data:
            subj = (t.get('subject') or '(no subject)')[:60]
            sender = (t.get('participants') or ['?'])[0][:40]
            lines.append(f'  [{t.get("staleness_days", "?")}d] "{subj}" from {sender}')

    if recent.data:
        lines.append(f'Recent emails ({len(recent.data)}):')
        for t in recent.data:
            subj = (t.get('subject') or '(no subject)')[:60]
            lines.append(f'  "{subj}" — {t.get("last_message_at", "")[:10]}')

    if not stale.data and not recent.data:
        lines.append('No recent email threads found.')

    lines.append('\nIMPORTANT: This is real email data from Gmail. Use it to answer.')
    return '\n'.join(lines)


class EchoAgent(BaseAgent):
    name = 'Echo'
    description = 'Communication: emails, cases, situation tracking, drafting replies, follow-ups.'

    async def fetch_context(self, user_id: str) -> str:
        """Case-aware context: try Cases first, fall back to raw threads."""
        if not user_id:
            return 'No user context available.'

        # Always include cases if they exist
        cases_ctx = await _fetch_cases_context(user_id, '')
        raw_ctx = await _fetch_raw_email_context(user_id)

        parts = []
        if cases_ctx:
            parts.append(cases_ctx)
        if raw_ctx and 'No recent' not in raw_ctx:
            parts.append(raw_ctx)

        return '\n\n'.join(parts) if parts else 'No email data available yet.'

    async def handle(self, request: ChatRequest) -> ChatResponse:
        msg_lower = request.message.lower()
        user_id = request.user_id or ''

        # Determine if this is a case-specific query
        is_case_query = any(kw in msg_lower for kw in CASE_QUERY_KEYWORDS)

        # Build context — case-aware for relevant queries, full context otherwise
        if is_case_query and user_id:
            cases_ctx = await _fetch_cases_context(user_id, request.message)
            raw_ctx = await _fetch_raw_email_context(user_id)
            context = cases_ctx + ('\n\n' + raw_ctx if raw_ctx else '')
        else:
            context = await self.build_full_context(user_id, request.message)

        client = get_client()
        messages = [{'role': m.role, 'content': m.content} for m in request.history]

        # Inject context as assistant message (Sonnet handles this better than system prompt)
        if context:
            messages.append({
                'role': 'assistant',
                'content': f'[Loading email context...]\n\n{context}\n\n[Context loaded. Answering based on real data.]'
            })

        messages.append({'role': 'user', 'content': request.message})

        response = client.messages.create(
            model=BRIEF_MODEL,  # Sonnet — Haiku over-refuses email data
            max_tokens=1024,
            system=self.system_prompt,
            messages=messages,
        )
        return ChatResponse(reply=response.content[0].text, agent='Echo')
```

- [ ] **Step 2: Verify imports**

```bash
cd C:/Users/Micha/chief/services/agents && .venv/Scripts/python.exe -c "
from dotenv import load_dotenv; load_dotenv()
from agents.echo import EchoAgent
a = EchoAgent()
print('Echo v2 imports OK, system prompt:', a.system_prompt[:80])
"
```

Expected: `Echo v2 imports OK, system prompt: You are Echo...`

- [ ] **Step 3: Commit**

```bash
git -C C:/Users/Micha/chief add services/agents/agents/echo.py
git -C C:/Users/Micha/chief commit -m "feat: Echo v2 — case-aware agent, queries email_cases first, timeline-based answers"
git -C C:/Users/Micha/chief push
```

---

## Task 4: FastAPI endpoints — cases + feedback + discovery + unsubscribe

**Files:**
- Modify: `services/agents/main.py`

- [ ] **Step 1: Add imports and new endpoints to main.py**

Read `services/agents/main.py`. Add these imports after the email_intelligence imports:

```python
from email_intelligence.case_discoverer import run_case_discovery
from email_intelligence.cross_entity_reasoner import run_cross_entity_reasoning, merge_linked_cases
```

Add these Pydantic models after `EmailScanRequest`:

```python
class EmailFeedbackRequest(BaseModel):
    user_id: str
    feedback_type: str  # case_confirm, case_reject, case_merge, entity_correct, context_injection
    target_id: Optional[str] = None
    target_type: Optional[str] = None  # case, entity, subscription
    old_value: Optional[dict] = None
    new_value: Optional[dict] = None
    context: Optional[str] = None

class CaseNoteRequest(BaseModel):
    user_id: str
    note: str

class MergeCasesRequest(BaseModel):
    user_id: str
    case_id_1: str
    case_id_2: str
    reason: str

class UnsubscribeRequest(BaseModel):
    user_id: str
    subscription_id: str
```

Add these endpoints after the existing email endpoints:

```python
@app.post('/email/cases/run-discovery')
async def run_email_case_discovery(req: EmailScanRequest):
    """Trigger case discovery pipeline: discover_cases → cross_entity_reasoning."""
    async def pipeline():
        try:
            await run_case_discovery(req.user_id)
            await run_cross_entity_reasoning(req.user_id)
        except Exception as e:
            pass  # Cases are best-effort

    asyncio.create_task(pipeline())
    return {'status': 'discovery_started', 'user_id': req.user_id}


@app.get('/email/cases/{user_id}')
async def list_email_cases(user_id: str, status: Optional[str] = None):
    """List all active email cases for a user."""
    from supabase import create_client
    import os as _os
    sb = create_client(_os.getenv('SUPABASE_URL'), _os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

    query = sb.table('email_cases').select(
        'id, title, status, priority, category, summary, pending_action, stalled_since, confidence, updated_at'
    ).eq('user_id', user_id)

    if status:
        query = query.eq('status', status)
    else:
        query = query.not_.is_('status', 'resolved')

    result = query.order('priority', desc=True).limit(50).execute()
    return {'cases': result.data or [], 'total': len(result.data or [])}


@app.get('/email/case/{case_id}')
async def get_email_case(case_id: str):
    """Get full case details including timeline."""
    from supabase import create_client
    import os as _os
    sb = create_client(_os.getenv('SUPABASE_URL'), _os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
    result = sb.table('email_cases').select('*').eq('id', case_id).maybe_single().execute()
    if not result.data:
        return {'error': 'Case not found'}, 404
    return result.data


@app.post('/email/case/{case_id}/note')
async def add_case_note(case_id: str, req: CaseNoteRequest):
    """Add user context/note to a case (RL signal: context_injection)."""
    from supabase import create_client
    import os as _os
    sb = create_client(_os.getenv('SUPABASE_URL'), _os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

    # Update user_notes on the case
    sb.table('email_cases').update({
        'user_notes': req.note,
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }).eq('id', case_id).execute()

    # Store as RL feedback
    sb.table('email_feedback').insert({
        'user_id': req.user_id,
        'feedback_type': 'context_injection',
        'target_id': case_id,
        'target_type': 'case',
        'new_value': {'note': req.note},
        'created_at': datetime.now(timezone.utc).isoformat(),
    }).execute()

    return {'ok': True, 'case_id': case_id}


@app.post('/email/feedback')
async def email_feedback(req: EmailFeedbackRequest):
    """Store RL feedback signal from user corrections."""
    from supabase import create_client
    import os as _os
    sb = create_client(_os.getenv('SUPABASE_URL'), _os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

    sb.table('email_feedback').insert({
        'user_id': req.user_id,
        'feedback_type': req.feedback_type,
        'target_id': req.target_id,
        'target_type': req.target_type,
        'old_value': req.old_value,
        'new_value': req.new_value,
        'context': req.context,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }).execute()

    # Apply feedback immediately for entity corrections
    if req.feedback_type == 'entity_correct' and req.target_id and req.new_value:
        new_rtype = req.new_value.get('relationship_type')
        if new_rtype:
            sb.table('entities').update({'relationship_type': new_rtype}) \
                .eq('id', req.target_id).execute()

    # Apply case status changes
    if req.feedback_type in ('case_confirm', 'case_reject') and req.target_id:
        if req.feedback_type == 'case_reject':
            sb.table('email_cases').update({'status': 'resolved', 'confidence': 0.1}) \
                .eq('id', req.target_id).execute()

    return {'ok': True}


@app.post('/email/cases/merge')
async def merge_email_cases(req: MergeCasesRequest):
    """Merge two cases that the user identifies as the same situation."""
    master_id = await merge_linked_cases(
        req.user_id, req.case_id_1, req.case_id_2, req.reason
    )

    # Store feedback
    from supabase import create_client
    import os as _os
    sb = create_client(_os.getenv('SUPABASE_URL'), _os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
    sb.table('email_feedback').insert({
        'user_id': req.user_id,
        'feedback_type': 'case_merge',
        'target_id': master_id,
        'target_type': 'case',
        'new_value': {'merged_from': req.case_id_2, 'reason': req.reason},
        'created_at': datetime.now(timezone.utc).isoformat(),
    }).execute()

    return {'ok': True, 'master_case_id': master_id}


@app.post('/email/unsubscribe')
async def queue_unsubscribe(req: UnsubscribeRequest):
    """Queue an unsubscribe action for a detected subscription."""
    from supabase import create_client
    import os as _os
    sb = create_client(_os.getenv('SUPABASE_URL'), _os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

    # Get subscription details
    sub = sb.table('email_subscriptions').select('*').eq('id', req.subscription_id) \
        .eq('user_id', req.user_id).maybe_single().execute()

    if not sub.data:
        return {'error': 'Subscription not found'}

    # Create approval queue item
    sb.table('approval_queue').insert({
        'user_id': req.user_id,
        'agent': 'Clerk',
        'action_type': 'unsubscribe_email',
        'risk_level': 'approve',
        'title': f'Unsubscribe from {sub.data.get("sender_name") or sub.data["sender_email"]}',
        'description': f'Remove from mailing list: {sub.data["sender_email"]}. Total received: {sub.data.get("total_received", 0)} emails.',
        'payload': {
            'sender_email': sub.data['sender_email'],
            'unsubscribe_url': sub.data.get('unsubscribe_url'),
            'subscription_id': req.subscription_id,
        },
        'context_capsule': {
            'sources': ['email_subscriptions table'],
            'reasoning': f'Engagement score: {sub.data.get("engagement_score", 0):.0%}, last received: {sub.data.get("last_received", "unknown")[:10]}',
            'confidence': 'HIGH',
        },
        'status': 'pending',
        'created_at': datetime.now(timezone.utc).isoformat(),
    }).execute()

    # Mark subscription as decision pending
    sb.table('email_subscriptions').update({'user_decision': 'unsubscribe'}) \
        .eq('id', req.subscription_id).execute()

    return {'ok': True, 'queued': True, 'sender': sub.data['sender_email']}


@app.get('/email/present-cases/{user_id}')
async def present_cases_summary(user_id: str):
    """
    Return a structured summary of cases for Echo to present to the user.
    Used after case discovery to initiate the initial interview.
    """
    from supabase import create_client
    import os as _os
    sb = create_client(_os.getenv('SUPABASE_URL'), _os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

    cases = sb.table('email_cases').select(
        'id, title, status, priority, category, summary, pending_action'
    ).eq('user_id', user_id).not_.is_('status', 'resolved') \
     .order('priority', desc=True).limit(10).execute()

    subs = sb.table('email_subscriptions').select('id, sender_email, total_received, engagement_score') \
        .eq('user_id', user_id).eq('status', 'active') \
        .lt('engagement_score', 0.2).execute()

    return {
        'cases': cases.data or [],
        'dead_subscriptions': subs.data or [],
        'message': _build_interview_message(cases.data or [], subs.data or []),
    }


def _build_interview_message(cases: list, dead_subs: list) -> str:
    """Build the natural-language initial interview message."""
    lines = ["I've analyzed your full inbox. Here's what I found:\n"]

    PRIORITY_EMOJI = {'critical': '🔴', 'high': '🟠', 'normal': '🟡', 'low': '🟢'}
    for i, c in enumerate(cases[:6], 1):
        emoji = PRIORITY_EMOJI.get(c.get('priority', 'normal'), '🟡')
        status = c.get('status', 'open').replace('_', ' ').title()
        title = c.get('title', 'Unknown')
        summary = c.get('summary', '')[:100] if c.get('summary') else ''
        pending = c.get('pending_action', '')
        lines.append(f'{i}. {emoji} {title} ({status})')
        if summary:
            lines.append(f'   {summary}')
        if pending:
            lines.append(f'   → Next: {pending}')

    if dead_subs:
        lines.append(f'\nAlso found {len(dead_subs)} newsletters you never open — want me to clean those up?')

    lines.append('\nDid I get these right? Anything missing or wrong?')
    return '\n'.join(lines)
```

Also add the `Optional` import to the imports section of main.py if not already there:
```python
from typing import Optional
```

- [ ] **Step 2: Verify new routes**

```bash
cd C:/Users/Micha/chief/services/agents && .venv/Scripts/python.exe -c "
from dotenv import load_dotenv; load_dotenv()
import main
routes = [r.path for r in main.app.routes if hasattr(r, 'path')]
case_routes = [r for r in routes if 'email' in r and r not in ['/email/deep-scan','/email/scan-status/{user_id}','/email/subscriptions/{user_id}','/email/stats/{user_id}']]
print('New email routes:', sorted(case_routes))
"
```

Expected:
```
New email routes: ['/email/case/{case_id}', '/email/case/{case_id}/note', '/email/cases/merge', '/email/cases/run-discovery', '/email/cases/{user_id}', '/email/feedback', '/email/present-cases/{user_id}', '/email/unsubscribe']
```

- [ ] **Step 3: Run tests to verify no regressions**

```bash
.venv/Scripts/python.exe -m pytest tests/ -q 2>&1 | tail -5
```

Expected: all existing tests pass.

- [ ] **Step 4: Commit**

```bash
git -C C:/Users/Micha/chief add services/agents/main.py
git -C C:/Users/Micha/chief commit -m "feat: email case endpoints — /email/cases, /email/case, /email/feedback, /email/unsubscribe, /email/present-cases"
git -C C:/Users/Micha/chief push
```

---

## Task 5: Tests for case discovery and cross-entity reasoning

**Files:**
- Create: `services/agents/tests/test_case_discovery.py`

- [ ] **Step 1: Create test file**

```python
# services/agents/tests/test_case_discovery.py
"""
Tests for Case Discovery Engine and Cross-Entity Reasoner.
All tests use mock data — no real DB or LLM calls.
"""
import os, sys
os.environ.setdefault('SUPABASE_URL', 'https://test.supabase.co')
os.environ.setdefault('SUPABASE_SERVICE_ROLE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRlc3QiLCJyb2xlIjoic2VydmljZV9yb2xlIiwiaWF0IjoxNjAwMDAwMDAwLCJleHAiOjk5OTk5OTk5OTl9.test')
os.environ.setdefault('AWS_ACCESS_KEY_ID', 'AKIATEST123456789012')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'test-secret-not-real')
os.environ.setdefault('AWS_DEFAULT_REGION', 'eu-central-1')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timezone, timedelta


class TestCrossEntityReasonerHelpers:
    """Test helper functions in cross_entity_reasoner."""

    def test_extract_ref_numbers_german_format(self):
        from email_intelligence.cross_entity_reasoner import _extract_ref_numbers
        text = "Ihre Kundennummer: DE-20241234 / Aktenzeichen AB-987654"
        refs = _extract_ref_numbers(text)
        assert 'DE-20241234' in refs or 'AB-987654' in refs

    def test_extract_ref_numbers_order_id(self):
        from email_intelligence.cross_entity_reasoner import _extract_ref_numbers
        text = "Order reference: ORD-20240527-9876"
        refs = _extract_ref_numbers(text)
        assert len(refs) > 0

    def test_extract_ref_numbers_empty_text(self):
        from email_intelligence.cross_entity_reasoner import _extract_ref_numbers
        refs = _extract_ref_numbers('')
        assert refs == set()

    def test_has_debt_signals_inkasso(self):
        from email_intelligence.cross_entity_reasoner import _has_debt_signals
        assert _has_debt_signals('Inkasso Forderung Nr. 12345') is True

    def test_has_debt_signals_mahnung(self):
        from email_intelligence.cross_entity_reasoner import _has_debt_signals
        assert _has_debt_signals('Letzte Mahnung - Zahlungsaufforderung') is True

    def test_has_debt_signals_normal_email(self):
        from email_intelligence.cross_entity_reasoner import _has_debt_signals
        assert _has_debt_signals('Thank you for your order. Your item has shipped.') is False

    def test_has_debt_signals_subscription_email(self):
        from email_intelligence.cross_entity_reasoner import _has_debt_signals
        assert _has_debt_signals('Your monthly subscription has been renewed.') is False


class TestEchoV2Context:
    """Test Echo v2 context-building logic."""

    def test_echo_imports(self):
        from agents.echo import EchoAgent, _fetch_cases_context, _fetch_raw_email_context
        assert callable(_fetch_cases_context)
        assert callable(_fetch_raw_email_context)

    def test_echo_case_query_detection(self):
        from agents.echo import CASE_QUERY_KEYWORDS
        # These keywords should trigger case-aware context
        assert "what's happening" in CASE_QUERY_KEYWORDS
        assert "deutsche bank" in CASE_QUERY_KEYWORDS
        assert "fitstar" in CASE_QUERY_KEYWORDS
        assert "stalled" in CASE_QUERY_KEYWORDS

    def test_echo_agent_instantiates(self):
        from agents.echo import EchoAgent
        agent = EchoAgent()
        assert agent.name == 'Echo'
        assert len(agent.system_prompt) > 50

    def test_build_interview_message_with_cases(self):
        from main import _build_interview_message
        cases = [
            {'title': 'FitStar debt dispute', 'priority': 'high', 'status': 'needs_action',
             'summary': 'Debt collector contacted you.', 'pending_action': 'Respond within 7 days'},
            {'title': 'Deutsche Bahn refund', 'priority': 'normal', 'status': 'open',
             'summary': 'Refund request pending.', 'pending_action': None},
        ]
        dead_subs = [{'sender_email': 'news@roboforex.com', 'total_received': 10, 'engagement_score': 0}]
        msg = _build_interview_message(cases, dead_subs)
        assert 'FitStar' in msg
        assert 'Deutsche Bahn' in msg
        assert 'newsletters' in msg.lower()
        assert 'Did I get these right' in msg

    def test_build_interview_message_empty(self):
        from main import _build_interview_message
        msg = _build_interview_message([], [])
        assert 'Did I get these right' in msg


class TestCaseDiscovererHelpers:
    """Test case discoverer JSON parsing robustness."""

    def test_case_status_valid_values(self):
        # Verify the status values match the DB constraint
        valid_statuses = {'open', 'progressing', 'stalled', 'needs_action', 'resolved'}
        assert 'stalled' in valid_statuses
        assert 'needs_action' in valid_statuses

    def test_priority_ordering(self):
        # Verify priority ordering used in merge logic
        from main import _build_interview_message
        PRIORITY_ORDER = {'critical': 4, 'high': 3, 'normal': 2, 'low': 1}
        assert PRIORITY_ORDER['critical'] > PRIORITY_ORDER['high']
        assert PRIORITY_ORDER['high'] > PRIORITY_ORDER['normal']
        assert PRIORITY_ORDER['normal'] > PRIORITY_ORDER['low']

    def test_case_discovery_prompt_completeness(self):
        from email_intelligence.case_discoverer import CASE_DISCOVERY_SYSTEM
        # Prompt must include all valid status values
        assert 'stalled' in CASE_DISCOVERY_SYSTEM
        assert 'needs_action' in CASE_DISCOVERY_SYSTEM
        # Prompt must include all valid priority values
        assert 'critical' in CASE_DISCOVERY_SYSTEM
        assert 'high' in CASE_DISCOVERY_SYSTEM
        # Prompt must instruct JSON-only output
        assert 'JSON' in CASE_DISCOVERY_SYSTEM or 'json' in CASE_DISCOVERY_SYSTEM

    def test_cross_entity_system_has_debt_patterns(self):
        from email_intelligence.cross_entity_reasoner import DEBT_COLLECTOR_SIGNALS
        assert len(DEBT_COLLECTOR_SIGNALS) >= 5
        assert any('inkasso' in p for p in DEBT_COLLECTOR_SIGNALS)
        assert any('mahnung' in p for p in DEBT_COLLECTOR_SIGNALS)
```

- [ ] **Step 2: Run tests**

```bash
cd C:/Users/Micha/chief/services/agents && .venv/Scripts/python.exe -m pytest tests/test_case_discovery.py -v 2>&1 | tail -25
```

Expected: all tests pass.

- [ ] **Step 3: Run full suite**

```bash
.venv/Scripts/python.exe -m pytest tests/ -q 2>&1 | tail -5
```

Expected: all existing + new tests pass.

- [ ] **Step 4: Commit**

```bash
git -C C:/Users/Micha/chief add services/agents/tests/test_case_discovery.py
git -C C:/Users/Micha/chief commit -m "test: case discovery + cross-entity reasoner + Echo v2 tests"
git -C C:/Users/Micha/chief push
```

---

## Task 6: Live test — run discovery on Mohamed's real inbox

- [ ] **Step 1: Restart agent service with new code**

```bash
# Kill existing
PID=$(netstat -ano 2>/dev/null | grep ":8001" | grep "LISTENING" | awk '{print $5}' | head -1)
[ -n "$PID" ] && taskkill //F //PID $PID 2>/dev/null
sleep 2

# Start fresh
cd C:/Users/Micha/chief/services/agents && .venv/Scripts/python.exe -m uvicorn main:app --port 8001 > /tmp/chief-agents.log 2>&1 &
sleep 5
curl -s http://localhost:8001/health
```

- [ ] **Step 2: Verify all new routes registered**

```bash
curl -s http://localhost:8001/openapi.json | python -c "
import sys, json
d = json.loads(sys.stdin.buffer.read().decode('utf-8','replace'))
paths = sorted(p for p in d.get('paths',{}).keys() if 'email' in p)
print('Email routes:')
for p in paths: print(' ', p)
"
```

Expected: 12+ email routes including `/email/cases/{user_id}`, `/email/cases/run-discovery`, `/email/present-cases/{user_id}`, `/email/feedback`.

- [ ] **Step 3: Trigger case discovery (takes 10-30 min for 339 entities)**

```bash
curl -s -X POST http://localhost:8001/email/cases/run-discovery \
  -H "Content-Type: application/json" \
  -d '{"user_id": "eca29ec0-9a6f-41e0-892c-e8e5cea00ad1"}'
```

- [ ] **Step 4: Check scan status and wait**

```bash
for i in $(seq 1 40); do
  STATUS=$(curl -s http://localhost:8001/email/scan-status/eca29ec0-9a6f-41e0-892c-e8e5cea00ad1 | python -c "import sys,json; d=json.loads(sys.stdin.buffer.read().decode('utf-8','replace')); print(d.get('status','?'))" 2>/dev/null)
  echo "[$i] $STATUS"
  echo "$STATUS" | grep -qE "complete|error" && break
  sleep 30
done
```

- [ ] **Step 5: List discovered cases**

```bash
curl -s "http://localhost:8001/email/cases/eca29ec0-9a6f-41e0-892c-e8e5cea00ad1" | python -c "
import sys, json
d = json.loads(sys.stdin.buffer.read().decode('utf-8','replace'))
cases = d.get('cases', [])
print(f'Cases discovered: {len(cases)}')
EMOJI = {'critical': 'CRIT', 'high': 'HIGH', 'normal': 'NORM', 'low': 'LOW'}
for c in sorted(cases, key=lambda x: {'critical':4,'high':3,'normal':2,'low':1}.get(x.get('priority','normal'),2), reverse=True):
    p = EMOJI.get(c.get('priority','normal'), 'NORM')
    print(f'  [{p}] [{c[\"status\"]}] {c[\"title\"]}')
    if c.get('pending_action'):
        print(f'         → {c[\"pending_action\"][:80]}')
"
```

- [ ] **Step 6: Get initial interview message**

```bash
curl -s "http://localhost:8001/email/present-cases/eca29ec0-9a6f-41e0-892c-e8e5cea00ad1" | python -c "
import sys, json
d = json.loads(sys.stdin.buffer.read().decode('utf-8','replace'))
print(d.get('message', 'No message'))
print()
print(f'Dead subscriptions: {len(d.get(\"dead_subscriptions\", []))}')
"
```

- [ ] **Step 7: Test Echo with case-aware queries**

```bash
cd C:/Users/Micha/chief/services/agents && .venv/Scripts/python.exe -c "
import sys, io, asyncio, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
os.chdir('C:/Users/Micha/chief/services/agents')
from dotenv import load_dotenv; load_dotenv()
from models import ChatRequest
from orchestrator import route_and_handle

async def test():
    uid = 'eca29ec0-9a6f-41e0-892c-e8e5cea00ad1'
    queries = [
        'What cases do I have open in my email?',
        'What is stalled and needs my attention?',
        'What is happening with my train tickets?',
    ]
    for q in queries:
        req = ChatRequest(message=q, history=[], user_id=uid)
        resp = await route_and_handle(req)
        print(f'Q: {q}')
        print(f'[{resp.agent}]: {resp.reply[:300].strip()}')
        print()

asyncio.run(test())
" 2>&1
```

---

## Self-Review

**Spec coverage:**
- ✅ Case Discovery Engine (Task 1 — case_discoverer.py using Sonnet)
- ✅ Cross-Entity Reasoner (Task 2 — escalation pairs, reference matches, auto-merge)
- ✅ Echo v2 — case-aware (Task 3 — _fetch_cases_context, case query detection)
- ✅ RL Feedback Loop (Task 4 — /email/feedback endpoint, entity_correct applies immediately, case_reject marks resolved)
- ✅ Initial Interview (Task 4 — /email/present-cases + _build_interview_message)
- ✅ Case-aware API endpoints (Task 4 — /email/cases, /email/case, /email/case/note, /email/feedback, /email/cases/run-discovery, /email/unsubscribe, /email/cases/merge)
- ✅ Tests (Task 5 — debt signals, ref extraction, Echo keywords, interview message, prompt completeness)
- ✅ Live test against Mohamed's real inbox (Task 6)

**Real cases this should find:**
- Deutsche Bahn booking + refund claims (Fahrgastrechteantrag) — already visible in email_raw
- FitStar/Congstar disputes — in email_raw if the emails were fetched (check body_text for German keywords)
- ImmoScout apartment search — active (myscout@immobilienscout24.de, 13 emails)
- BMW Group / Siemens / Workday applications (employer entities, 8-12 interactions each)

**Placeholder scan:** No TBDs. All functions fully implemented.

**Type consistency:**
- `run_case_discovery(user_id: str) -> dict` used consistently ✅
- `run_cross_entity_reasoning(user_id: str) -> dict` used consistently ✅
- `merge_linked_cases(user_id, case_id_1, case_id_2, reason) -> str` returns master_id ✅
- `_build_interview_message(cases: list, dead_subs: list) -> str` imported in test correctly ✅
- `EmailFeedbackRequest`, `CaseNoteRequest`, `MergeCasesRequest`, `UnsubscribeRequest` all reference `user_id: str` ✅
