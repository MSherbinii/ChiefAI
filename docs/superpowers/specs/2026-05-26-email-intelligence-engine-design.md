# Email Intelligence Engine v2 — Design Specification

## Problem Statement

The current email connector is naive: fetch 50 newest threads, show subjects to the LLM. This serves no purpose over opening Gmail directly. Users need an AI that understands the *structure* of their email life — ongoing situations, entity relationships, subscription patterns, and pending actions — not just a reverse-chronological list.

## Core Concept

Chief doesn't just read your inbox — it builds a **model of your email life**, discovers ongoing **situations** (Cases), identifies **who matters** (Entities), detects **recurring noise** (Subscriptions), and reasons about **what needs action** across all of these.

## Data Model (5 Layers)

### Layer 1: Raw Email Store (`email_raw`)

Complete inbox scan — every email, not just recent.

```sql
create table public.email_raw (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.profiles(id) on delete cascade,
  gmail_id        text not null,           -- Gmail message ID
  thread_id       text not null,           -- Gmail thread ID
  from_email      text not null,
  from_name       text,
  to_emails       text[],
  subject         text,
  snippet         text,                    -- first 500 chars of body
  body_text       text,                    -- full plain-text body (for case reasoning)
  date            timestamptz not null,
  labels          text[],                  -- Gmail labels: INBOX, SENT, STARRED, etc.
  is_sent         boolean default false,   -- user sent this
  is_read         boolean default true,
  has_attachments boolean default false,
  in_reply_to     text,                    -- message-id of parent
  embedding       vector(1536),
  processed       boolean default false,   -- has been through intelligence pipeline
  created_at      timestamptz default now(),
  unique(user_id, gmail_id)
);
```

### Layer 2: Entities (upgraded)

Existing `entities` table gets new fields for email intelligence:

```sql
-- Add to existing entities table
alter table public.entities add column if not exists
  relationship_type text;   -- service_provider, bank, debt_collector, employer, professor, newsletter, marketplace, government, friend, unknown

alter table public.entities add column if not exists
  email_domains text[] default '{}';  -- ["immoscout24.de", "is24.de"]

alter table public.entities add column if not exists
  first_contact timestamptz;

alter table public.entities add column if not exists
  last_contact timestamptz;

alter table public.entities add column if not exists
  interaction_count integer default 0;

alter table public.entities add column if not exists
  engagement_score real default 0;  -- 0-1: how much user interacts with this entity
```

### Layer 3: Cases (`email_cases`)

A Case is an ongoing situation spanning multiple emails and potentially multiple entities.

```sql
create table public.email_cases (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.profiles(id) on delete cascade,
  title           text not null,           -- "Fitstar debt collection dispute"
  status          text default 'open',     -- open, progressing, stalled, needs_action, resolved
  priority        text default 'normal',   -- low, normal, high, critical
  category        text,                    -- dispute, account_setup, application, purchase, service_request
  summary         text,                    -- AI-generated summary of the full case
  entities        uuid[] default '{}',     -- entity IDs involved
  email_ids       uuid[] default '{}',     -- email_raw IDs in this case
  thread_ids      text[] default '{}',     -- Gmail thread IDs
  pending_action  text,                    -- what the user needs to do next
  stalled_since   timestamptz,             -- when did progress stop?
  user_notes      text,                    -- context the user provided verbally
  timeline        jsonb default '[]',      -- [{date, event, source}]
  confidence      real default 0.7,        -- how confident is the case grouping?
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);
alter table public.email_cases enable row level security;
create policy "Users own their cases"
  on public.email_cases for all using (auth.uid() = user_id);
```

### Layer 4: Subscriptions (`email_subscriptions`)

Detected from email patterns — no LLM needed for most.

```sql
create table public.email_subscriptions (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.profiles(id) on delete cascade,
  entity_id       uuid references public.entities(id),
  sender_email    text not null,
  sender_name     text,
  frequency       text,                    -- daily, weekly, monthly, irregular
  avg_interval_days real,
  total_received  integer default 0,
  last_received   timestamptz,
  opened_count    integer default 0,       -- approximation from read status
  replied_count   integer default 0,
  engagement_score real default 0,         -- 0-1
  has_unsubscribe_link boolean default false,
  unsubscribe_url text,
  status          text default 'active',   -- active, unsubscribed, paused
  user_decision   text,                    -- keep, unsubscribe, undecided
  created_at      timestamptz default now(),
  unique(user_id, sender_email)
);
alter table public.email_subscriptions enable row level security;
create policy "Users own their subscriptions"
  on public.email_subscriptions for all using (auth.uid() = user_id);
```

### Layer 5: Email Feedback (`email_feedback`)

RL training signal from user corrections.

```sql
create table public.email_feedback (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.profiles(id) on delete cascade,
  feedback_type   text not null,           -- case_confirm, case_reject, case_merge, entity_correct, priority_change, action_approve, action_reject
  target_id       uuid,                    -- case_id or entity_id
  target_type     text,                    -- 'case' or 'entity' or 'subscription'
  old_value       jsonb,
  new_value       jsonb,
  context         text,                    -- user's explanation if any
  created_at      timestamptz default now()
);
alter table public.email_feedback enable row level security;
create policy "Users own their feedback"
  on public.email_feedback for all using (auth.uid() = user_id);
```

## Processing Pipeline

### Phase 1: Deep Scan (runs once on Gmail connect)

```python
async def deep_scan_inbox(user_id: str):
    """
    Scan ALL emails in user's Gmail account.
    Uses Gmail API pagination (500 per page).
    Stores everything in email_raw.
    Takes 3-10 minutes depending on inbox size.
    """
    # Fetch ALL message IDs (lightweight — just IDs)
    # Then batch-fetch full message metadata
    # Store in email_raw with processed=False
    # Also fetch SENT folder separately (critical for case detection)
    # Total: typically 2000-10000 emails for an active user
```

### Phase 2: Entity Clustering (after deep scan)

```python
async def cluster_entities(user_id: str):
    """
    Group emails by sender domain → create/update entities.
    Classify entity relationship_type using LLM.
    
    Clustering rules:
    - Same domain = same entity (noreply@db.de + service@db.de → Deutsche Bank)
    - Exception: personal emails from the same domain are separate entities
    - LLM classifies relationship_type from sender patterns
    """
```

### Phase 3: Subscription Detection (pattern matching)

```python
async def detect_subscriptions(user_id: str):
    """
    Find recurring senders with newsletter patterns.
    No LLM needed — pure pattern matching:
    - Same sender emails 3+ times
    - Regular interval (±30% variance)
    - Contains unsubscribe link (detected from headers/body)
    - Low engagement (never replied, often unread)
    """
```

### Phase 4: Case Discovery (LLM reasoning)

```python
async def discover_cases(user_id: str):
    """
    The core intelligence: find ongoing SITUATIONS in the email.
    
    Signals that indicate a Case exists:
    - User SENT emails to this entity (not just received)
    - Multiple threads about the same topic with same entity
    - Mentions: money, deadlines, reference numbers, account numbers
    - Escalation: entity changes (company → debt collector)
    - Temporal clustering: burst of activity then silence (stalled)
    
    Process:
    1. For each non-newsletter entity with sent_count > 0:
       Fetch all threads (sent + received)
    2. Feed to LLM with prompt: "Identify distinct Cases (situations)"
    3. For each case: determine status, pending action, priority
    4. Cross-reference: find cases that span multiple entities
    """
```

### Phase 5: Cross-Entity Reasoning

```python
async def cross_entity_reasoning(user_id: str):
    """
    Find cases that SPAN multiple entities.
    
    Patterns:
    - Company A emails stop → Collection agency B emails start = dispute escalation
    - Bank emails + your sent email + silence = stalled application
    - Multiple entities mention same reference number = linked case
    
    This is what makes Chief see what Gmail can't:
    the STORY across entities and time.
    """
```

### Phase 6: Initial Interview

After processing completes, Chief presents its findings and asks for confirmation:

```
"I scanned your full inbox and found these active situations:

1. 🔴 Fitstar/McFit dispute → debt collector (HIGH priority — needs response)
2. 🟡 Deutsche Bank account setup → waiting 14 days (STALLED)
3. 🟡 Congstar billing issue → may escalate
4. 🟢 Apartment search via ImmoScout24 (ACTIVE)

Also found: 47 newsletter subscriptions (12 you never open — want me to clean up?)

Did I get these right? Anything I'm missing?"
```

User confirms, corrects, or adds context → stored as RL signal.

## Reinforcement Learning Loop

### Signal Sources

| Signal | Source | Weight |
|--------|--------|--------|
| Case confirmation | User says "yes, correct" | +1.0 |
| Case rejection | User says "no, wrong" | -1.0 |
| Case merge | User says "these are the same" | Relationship signal |
| Priority override | User changes priority | Priority model update |
| Action approval | User approves suggested action | +0.5 on action type |
| Action rejection | User rejects action | -0.5 on action type |
| Implicit attention | User asks about a case | +0.2 priority boost |
| Implicit ignore | User never mentions a case | -0.1 priority decay |
| Context injection | User explains situation verbally | Store as case note |

### Learning Outcomes

1. **Entity classification improves**: After confirming "Inkasso is a debt collector" for 2 entities, Chief zero-shots new debt collector emails.
2. **Case priority improves**: Learning that disputes are always high-priority for this user.
3. **Action templates**: After user approves 3 similar follow-up emails, Chief pre-drafts the next one.
4. **Subscription preferences**: User keeps tech newsletters, unsubscribes marketing → future detection is smarter.

## Echo Agent v2 (Case-Aware)

Echo transforms from "summarize threads" to "situation navigator":

```
User: "What's happening with Deutsche Bank?"

Echo v2:
"📋 Case: Deutsche Bank Account Setup
Status: STALLED (14 days no response)

Timeline:
• May 12 — Application submitted online
• May 13 — Confirmation received (Ref: DB-2026-44521)  
• May 15 — Identity verification link received
• May 15 — You completed verification (sent confirmation)
• Since then — No response. No card. No login details.

⚡ Suggested: Send follow-up email referencing application DB-2026-44521.
   Draft ready — approve?"
```

## Subscription Cleanup Feature

Detected autonomously, presented as a batch action:

```
"📧 Subscription Cleanup

Found 47 recurring senders. Breakdown:
• 12 — Never opened (safe to unsubscribe)
• 8 — Opened but never clicked
• 15 — Occasional engagement
• 12 — Active engagement (keep)

Quick actions:
1. Mass-unsubscribe 12 dead subscriptions (saves ~15 emails/week)
2. Review the 8 low-engagement ones
3. Show full list

Each unsubscribe goes through your approval queue."
```

## API Endpoints (New)

```
POST /email/deep-scan          — trigger full inbox scan
GET  /email/cases/{user_id}    — list all active cases
GET  /email/case/{case_id}     — full case with timeline
POST /email/case/{case_id}/note — add user context to a case
POST /email/subscriptions      — list detected subscriptions
POST /email/unsubscribe        — queue unsubscribe action
POST /email/feedback           — RL feedback signal
GET  /email/scan-status        — check progress of deep scan
```

## Implementation Order

1. **Migration**: Create email_raw, email_cases, email_subscriptions, email_feedback tables
2. **Deep Scanner**: Gmail API full-inbox scan with pagination
3. **Entity Clustering**: Group by domain, classify relationship_type
4. **Subscription Detector**: Pattern matching on frequency + engagement
5. **Case Discovery Engine**: LLM-based situation identification
6. **Cross-Entity Reasoner**: Link cases across entities
7. **Echo v2**: Case-aware response generation
8. **RL Feedback Loop**: Store and apply user corrections
9. **Subscription Cleanup UI**: Frontend for batch unsubscribe
10. **Initial Interview Flow**: Present findings, get user confirmation

## Success Criteria

1. Chief identifies the Deutsche Bank stalled situation without being told
2. Chief links fitstar emails to the debt collector as one case
3. Chief detects 40+ newsletters and correctly separates them from real correspondence
4. After user confirms 2-3 cases, future case detection accuracy improves
5. "What's happening with [entity]?" gives a full timeline, not just recent emails
