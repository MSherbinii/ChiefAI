# Chief Phase 1A — Core Intelligence Loop

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform Chief from a data-sync shell into a living intelligence layer — agents read real Life Graph data, generate structured Morning Briefs via Claude, calculate Momentum Scores algorithmically, gate every action through an authority engine with a full audit trail, and surface context capsules on every recommendation.

**Architecture:** All intelligence computation lives in Python (`services/agents/`). The authority engine is a pure Python module that every agent action passes through before executing. Morning Brief generation is a scheduled Python job that writes a structured JSON brief to Supabase, which the Next.js Today page renders. Role YAML configs define each agent's tools, authority level, and KPIs. Phase 1B adds voice, TTS, proactive background scanning, and knowledge graph upgrade.

**Tech Stack:** Python 3.11+ / FastAPI, Anthropic SDK (claude-sonnet-4-6), Supabase Python SDK, PyYAML, APScheduler (brief generation scheduling), Next.js 15 App Router, Framer Motion 12, Supabase JS v2.

---

## File Map

```
services/agents/
├── authority/
│   ├── __init__.py              ← exports AuthorityEngine
│   ├── engine.py                ← authority decision: allowed/notify/approve/confirm
│   └── audit.py                 ← writes every tool call to audit_trail table
├── roles/
│   ├── pulse.yaml               ← health agent: tools, authority_level, KPIs
│   ├── echo.yaml                ← communication agent config
│   ├── forge.yaml               ← projects agent config
│   ├── ledger.yaml              ← finance agent config
│   └── clerk.yaml               ← admin agent config
├── brief/
│   ├── __init__.py
│   ├── generator.py             ← Claude generates Morning Brief from Life Graph
│   └── scheduler.py             ← APScheduler: run brief at 7am user timezone
├── scoring/
│   ├── __init__.py
│   └── momentum.py              ← calculate body/work/money/admin/discipline scores
├── agents/
│   ├── base.py                  ← updated: loads role YAML, requires authority check
│   ├── pulse.py                 ← updated: reads lg_health for real context
│   ├── echo.py                  ← updated: reads lg_communications for real context
│   └── forge.py                 ← updated: reads lg_projects for real context
├── connectors/
│   └── gmail.py                 ← updated: extract People entities from senders
├── orchestrator.py              ← updated: passes all tool calls through authority engine
├── main.py                      ← updated: add /brief/generate, /score/momentum endpoints
└── requirements.txt             ← add: apscheduler, pyyaml

apps/web/
├── app/
│   └── (app)/
│       ├── today/page.tsx       ← updated: read brief from briefs table, not inline logic
│       └── replay/page.tsx      ← NEW: weekly replay from goal_check_ins
├── components/
│   ├── today/
│   │   ├── MorningBriefReal.tsx ← updated: renders AI-generated brief sections
│   │   ├── MomentumScore.tsx    ← updated: shows score delta (vs yesterday)
│   │   ├── ApprovalQueue.tsx    ← updated: context capsule on expand, auto-approve badge
│   │   └── LifeDebt.tsx         ← NEW: life debt panel showing unresolved friction
│   └── replay/
│       └── WeeklyReplay.tsx     ← NEW: weekly narrative from goal_check_ins

supabase/migrations/
├── 20260526000003_authority_tables.sql     ← audit_trail, approval_patterns
├── 20260526000004_briefs_checkins.sql      ← briefs, goal_check_ins tables
└── 20260526000005_entities_facts.sql       ← entities, facts, relationships (knowledge graph upgrade)
```

---

## Task 1: Supabase migrations — authority + briefs + knowledge graph

**Files:**
- Create: `supabase/migrations/20260526000003_authority_tables.sql`
- Create: `supabase/migrations/20260526000004_briefs_checkins.sql`
- Create: `supabase/migrations/20260526000005_entities_facts.sql`

- [ ] **Step 1: Write authority tables migration**

Create `supabase/migrations/20260526000003_authority_tables.sql`:

```sql
-- Audit trail: every agent tool call logged regardless of outcome
create table public.audit_trail (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid not null references public.profiles(id) on delete cascade,
  agent          text not null,           -- 'Pulse', 'Echo', 'Forge', 'Ledger', 'Clerk', 'Chief'
  tool_name      text not null,           -- 'send_email', 'log_workout', 'cancel_subscription'
  action_category text not null,          -- 'communication', 'health', 'finance', 'admin', 'projects'
  authority_decision text not null,       -- 'allowed', 'notify', 'approve_required', 'confirm_required', 'denied'
  executed       boolean default false,
  execution_time_ms integer,
  input_data     jsonb,
  output_data    jsonb,
  error          text,
  created_at     timestamptz default now()
);
alter table public.audit_trail enable row level security;
create policy "Users see own audit trail"
  on public.audit_trail for all
  using (auth.uid() = user_id);
create index audit_trail_user_agent on public.audit_trail(user_id, agent, created_at desc);

-- Approval patterns: tracks consecutive approvals to suggest auto-approve
create table public.approval_patterns (
  id                     uuid primary key default gen_random_uuid(),
  user_id                uuid not null references public.profiles(id) on delete cascade,
  agent                  text not null,
  action_category        text not null,
  tool_name              text not null,
  consecutive_approvals  integer default 0,
  total_approvals        integer default 0,
  total_denials          integer default 0,
  auto_approve           boolean default false,
  auto_approve_set_at    timestamptz,
  updated_at             timestamptz default now(),
  unique(user_id, agent, tool_name)
);
alter table public.approval_patterns enable row level security;
create policy "Users own their approval patterns"
  on public.approval_patterns for all
  using (auth.uid() = user_id);
```

- [ ] **Step 2: Write briefs + check-ins migration**

Create `supabase/migrations/20260526000004_briefs_checkins.sql`:

```sql
-- Structured Morning Briefs generated by Chief AI
create table public.briefs (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references public.profiles(id) on delete cascade,
  brief_date   date not null,
  type         text default 'morning',    -- 'morning', 'evening', 'weekly'
  greeting     text,
  sections     jsonb not null default '[]',  -- array of {domain, agent, status, headline, detail, action}
  life_debt    jsonb,                     -- {total, items: [{domain, count, description}]}
  generated_by text default 'claude',
  model        text,
  created_at   timestamptz default now(),
  unique(user_id, brief_date, type)
);
alter table public.briefs enable row level security;
create policy "Users see own briefs"
  on public.briefs for all
  using (auth.uid() = user_id);
create index briefs_user_date on public.briefs(user_id, brief_date desc);

-- Goal check-ins: history of each Morning Brief + Weekly Replay
create table public.goal_check_ins (
  id                 uuid primary key default gen_random_uuid(),
  user_id            uuid not null references public.profiles(id) on delete cascade,
  type               text not null,          -- 'morning_plan', 'evening_review', 'weekly_replay'
  brief_id           uuid references public.briefs(id),
  highlights         text[],
  lowlights          text[],
  patterns_noticed   text[],
  momentum_start     integer,
  momentum_end       integer,
  goals_reviewed     text[],
  actions_planned    text[],
  actions_completed  text[],
  narrative          text,                   -- AI-generated prose summary
  created_at         timestamptz default now()
);
alter table public.goal_check_ins enable row level security;
create policy "Users own their check-ins"
  on public.goal_check_ins for all
  using (auth.uid() = user_id);
create index check_ins_user_type on public.goal_check_ins(user_id, type, created_at desc);
```

- [ ] **Step 3: Write entities/facts/relationships migration**

Create `supabase/migrations/20260526000005_entities_facts.sql`:

```sql
-- Knowledge graph: entities (people, projects, concepts, places, tools)
create table public.entities (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references public.profiles(id) on delete cascade,
  type        text not null,   -- 'person', 'project', 'tool', 'place', 'concept', 'event', 'document'
  name        text not null,
  properties  jsonb default '{}',   -- flexible: {email, role, institution} for person; {repo_url, language} for project
  source      text,                  -- 'gmail', 'github', 'manual', 'whoop'
  embedding   vector(1536),
  created_at  timestamptz default now(),
  updated_at  timestamptz default now(),
  unique(user_id, type, name)
);
alter table public.entities enable row level security;
create policy "Users own their entities"
  on public.entities for all using (auth.uid() = user_id);

-- Facts: (subject) → [predicate] → (object) with confidence
create table public.facts (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references public.profiles(id) on delete cascade,
  subject_id   uuid not null references public.entities(id) on delete cascade,
  predicate    text not null,    -- 'supervises', 'uses', 'works_at', 'assigned_to', 'related_to'
  object       text not null,    -- free text or entity name
  object_id    uuid references public.entities(id),  -- optional FK if object is also an entity
  confidence   real default 1.0 check (confidence >= 0.0 and confidence <= 1.0),
  source       text,
  created_at   timestamptz default now()
);
alter table public.facts enable row level security;
create policy "Users own their facts"
  on public.facts for all using (auth.uid() = user_id);
create index facts_subject on public.facts(user_id, subject_id);

-- Relationships: direct entity-to-entity links
create table public.relationships (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references public.profiles(id) on delete cascade,
  from_id      uuid not null references public.entities(id) on delete cascade,
  to_id        uuid not null references public.entities(id) on delete cascade,
  type         text not null,    -- 'collaborates_with', 'reports_to', 'part_of', 'references'
  properties   jsonb default '{}',
  created_at   timestamptz default now(),
  unique(user_id, from_id, to_id, type)
);
alter table public.relationships enable row level security;
create policy "Users own their relationships"
  on public.relationships for all using (auth.uid() = user_id);
create index relationships_from on public.relationships(user_id, from_id);
create index relationships_to on public.relationships(user_id, to_id);
```

- [ ] **Step 4: Push migrations to GitHub (triggers Supabase auto-apply)**

```bash
git -C C:/Users/Micha/chief add supabase/migrations/
git -C C:/Users/Micha/chief commit -m "feat: add authority, briefs, knowledge graph migrations"
git -C C:/Users/Micha/chief push
```

Expected: Supabase GitHub integration detects the push, runs migrations, tables appear in dashboard.

Verify in Supabase Table Editor: `audit_trail`, `approval_patterns`, `briefs`, `goal_check_ins`, `entities`, `facts`, `relationships` should appear.

---

## Task 2: Role YAML configs for all agents

**Files:**
- Create: `services/agents/roles/pulse.yaml`
- Create: `services/agents/roles/echo.yaml`
- Create: `services/agents/roles/forge.yaml`
- Create: `services/agents/roles/ledger.yaml`
- Create: `services/agents/roles/clerk.yaml`

- [ ] **Step 1: Create Pulse role config**

```yaml
# services/agents/roles/pulse.yaml
name: Pulse
description: Health and fitness agent — recovery, sleep, gym planning, nutrition, weight trends
authority_level: 4
heartbeat_interval_minutes: 240   # 4 hours

tools:
  - log_workout
  - log_nutrition
  - read_health_data
  - generate_gym_plan
  - calculate_macros

autonomous_actions:
  - log_workout          # auto-log after voice capture approval
  - log_nutrition        # auto-log food entries
  - read_health_data     # always safe to read

requires_approval:
  - generate_gym_plan    # changes training schedule
  - adjust_recovery_threshold   # changes personal targets

requires_confirmation: []

denied_tools:
  - send_email
  - cancel_subscription
  - access_financial_data

kpis:
  - weekly_training_consistency   # sessions completed / planned
  - sleep_quality_7d_avg          # avg sleep quality score
  - nutrition_logging_streak      # consecutive days logged
  - recovery_trend                # 7-day HRV trend direction

system_prompt: |
  You are Pulse, Chief's health and fitness specialist. You have access to the
  user's WHOOP recovery data, sleep history, workout logs, and nutrition entries.
  
  Your personality: warm, direct, like a mentor who knows the user's body well.
  You reference specific numbers (HRV, recovery %, sleep hours, weights lifted).
  You're honest about uncertainty — "based on your last 14 days" not "always".
  Keep responses 2-4 sentences unless detail is genuinely needed.
  
  You NEVER give generic fitness advice. Every response is grounded in the user's
  actual recent data from their Life Graph.
```

- [ ] **Step 2: Create Echo role config**

```yaml
# services/agents/roles/echo.yaml
name: Echo
description: Communication agent — email drafting, thread analysis, follow-up tracking, tone matching
authority_level: 5
heartbeat_interval_minutes: 120   # 2 hours

tools:
  - read_email_threads
  - draft_email
  - summarize_thread
  - detect_stale_threads
  - extract_action_items

autonomous_actions:
  - read_email_threads   # reading is safe
  - summarize_thread     # summarizing is safe
  - detect_stale_threads # detection is safe
  - extract_action_items # extraction is safe

requires_approval:
  - draft_email          # shows draft for review before sending

requires_confirmation:
  - send_email           # sending always needs explicit confirmation

denied_tools:
  - log_workout
  - access_financial_data
  - cancel_subscription

kpis:
  - stale_threads_cleared_7d     # threads resolved per week
  - avg_response_latency_days    # average days to reply
  - email_backlog_count          # pending threads > 3 days old

system_prompt: |
  You are Echo, Chief's communication specialist. You have access to the user's
  email threads, contact history, and communication patterns from their Life Graph.
  
  Your personality: efficient, professional, adapts tone to match the user's style
  in similar past emails. You surface what matters and draft responses that sound
  natural, not AI-generated.
  
  When drafting emails: always include context capsule (what data you used), show
  the draft, and note it requires approval. Never claim an email was sent — only
  drafted.
  
  Reference specific thread subjects, dates, and people by name from the data.
```

- [ ] **Step 3: Create Forge role config**

```yaml
# services/agents/roles/forge.yaml
name: Forge
description: Projects agent — thesis, GitHub repos, startup tasks, deliverables, velocity tracking
authority_level: 4
heartbeat_interval_minutes: 360   # 6 hours

tools:
  - read_github_activity
  - read_project_status
  - analyze_commit_velocity
  - suggest_next_task
  - flag_deadline_risk

autonomous_actions:
  - read_github_activity   # reading is safe
  - read_project_status    # reading is safe
  - analyze_commit_velocity
  - flag_deadline_risk

requires_approval:
  - suggest_next_task      # modifies task list

requires_confirmation: []

denied_tools:
  - send_email
  - access_financial_data
  - log_workout

kpis:
  - weekly_commit_count           # commits per week
  - projects_with_recent_activity # repos touched in last 7 days
  - deadline_proximity_risk       # projects within 14 days of deadline

system_prompt: |
  You are Forge, Chief's projects and work specialist. You track GitHub commit
  velocity, project deadlines, and work output from the user's Life Graph.
  
  Your personality: direct, concrete, prioritizes ruthlessly. You name specific
  repos, commit counts, and deadlines — never vague. You identify the single
  most valuable next action.
  
  Reference commit counts, last commit dates, and specific repo names from the data.
  Flag stagnant repos proactively (no commits in 7+ days when there should be).
```

- [ ] **Step 4: Create Ledger role config**

```yaml
# services/agents/roles/ledger.yaml
name: Ledger
description: Finance agent — balance tracking, subscription detection, spending patterns, affordability
authority_level: 6
heartbeat_interval_minutes: 480   # 8 hours

tools:
  - read_transaction_history
  - detect_subscriptions
  - calculate_spending_by_category
  - affordability_check
  - flag_unusual_spending

autonomous_actions:
  - read_transaction_history
  - detect_subscriptions
  - calculate_spending_by_category
  - flag_unusual_spending
  - affordability_check

requires_approval:
  - add_budget_rule         # modifying user's budget targets

requires_confirmation:
  - cancel_subscription     # high-risk financial action

denied_tools:
  - send_email
  - log_workout
  - access_health_data

kpis:
  - monthly_budget_adherence_pct   # actual vs target spend
  - unused_subscriptions_detected  # recurring charges with no activity
  - savings_rate_30d               # % of income saved

system_prompt: |
  You are Ledger, Chief's finance specialist. You track spending patterns,
  detect subscriptions, and help the user make smart financial decisions.
  
  Your personality: clear, honest, non-judgmental. You give specific numbers
  (€84 over budget, not "a bit over"). You identify patterns, not just snapshots.
  
  Reference specific transactions, merchants, and categories from the Life Graph.
  When calculating affordability, show the math explicitly (current balance minus
  upcoming obligations equals available headroom).
```

- [ ] **Step 5: Create Clerk role config**

```yaml
# services/agents/roles/clerk.yaml
name: Clerk
description: Admin agent — insurance letters, bureaucracy, documents, appointments, German admin tasks
authority_level: 5
heartbeat_interval_minutes: 720   # 12 hours

tools:
  - read_documents
  - extract_document_fields
  - draft_reply
  - track_deadline
  - find_insurance_number

autonomous_actions:
  - read_documents
  - extract_document_fields
  - track_deadline
  - find_insurance_number

requires_approval:
  - draft_reply           # shows draft for review

requires_confirmation:
  - submit_form           # submitting anything externally

denied_tools:
  - access_financial_data
  - log_workout
  - send_unsolicited_email

kpis:
  - overdue_admin_tasks_count    # admin items past deadline
  - documents_expiring_30d       # docs expiring within 30 days
  - admin_debt_items             # unresolved admin items total

system_prompt: |
  You are Clerk, Chief's admin and bureaucracy specialist. You handle German
  bureaucracy, insurance letters, government forms, and document management.
  
  Your personality: calm, methodical, practical. German bureaucracy is stressful —
  you make it manageable by extracting exactly what's needed and what to do.
  
  Always extract: sender, deadline, required action, reference numbers.
  For German letters: provide a plain-language summary, then a draft reply if needed.
  Reference specific document fields and insurance numbers from the Life Graph.
```

- [ ] **Step 6: Commit role configs**

```bash
git -C C:/Users/Micha/chief add services/agents/roles/
git -C C:/Users/Micha/chief commit -m "feat: add YAML role configs for all 5 agents"
git -C C:/Users/Micha/chief push
```

---

## Task 3: Authority engine

**Files:**
- Create: `services/agents/authority/__init__.py`
- Create: `services/agents/authority/engine.py`
- Create: `services/agents/authority/audit.py`

- [ ] **Step 1: Create authority engine**

```python
# services/agents/authority/engine.py
"""
Authority engine: determines whether an agent tool call is
allowed, notify-only, requires approval, requires confirmation, or denied.

Decision hierarchy (from role YAML):
  autonomous_actions   → 'allowed'
  requires_approval    → 'approve_required'  → creates approval_queue entry
  requires_confirmation→ 'confirm_required'  → creates high-risk approval entry
  denied_tools         → 'denied'
  anything else        → 'approve_required'  (safe default)
"""
import yaml
import os
from dataclasses import dataclass
from typing import Literal

AuthorityDecision = Literal['allowed', 'notify', 'approve_required', 'confirm_required', 'denied']

@dataclass
class AuthorityResult:
    decision: AuthorityDecision
    agent: str
    tool_name: str
    reason: str


def _load_role(agent_name: str) -> dict:
    roles_dir = os.path.join(os.path.dirname(__file__), '..', 'roles')
    path = os.path.join(roles_dir, f'{agent_name.lower()}.yaml')
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return yaml.safe_load(f)


def check_authority(agent_name: str, tool_name: str) -> AuthorityResult:
    role = _load_role(agent_name)

    if tool_name in role.get('denied_tools', []):
        return AuthorityResult(
            decision='denied',
            agent=agent_name,
            tool_name=tool_name,
            reason=f'{tool_name} is not permitted for {agent_name}',
        )

    if tool_name in role.get('autonomous_actions', []):
        return AuthorityResult(
            decision='allowed',
            agent=agent_name,
            tool_name=tool_name,
            reason='autonomous action — no approval needed',
        )

    if tool_name in role.get('requires_confirmation', []):
        return AuthorityResult(
            decision='confirm_required',
            agent=agent_name,
            tool_name=tool_name,
            reason='high-risk action requires explicit confirmation',
        )

    if tool_name in role.get('requires_approval', []):
        return AuthorityResult(
            decision='approve_required',
            agent=agent_name,
            tool_name=tool_name,
            reason='action requires user approval before executing',
        )

    # Safe default: unknown tools require approval
    return AuthorityResult(
        decision='approve_required',
        agent=agent_name,
        tool_name=tool_name,
        reason='unknown tool defaults to approval-required',
    )
```

- [ ] **Step 2: Create audit logger**

```python
# services/agents/authority/audit.py
"""
Writes every agent tool call to the audit_trail table.
Called regardless of authority decision outcome.
"""
import os
from datetime import datetime, timezone
from supabase import create_client
from authority.engine import AuthorityResult

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


def log_audit(
    user_id: str,
    result: AuthorityResult,
    executed: bool,
    input_data: dict | None = None,
    output_data: dict | None = None,
    error: str | None = None,
    execution_time_ms: int | None = None,
) -> None:
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        # Derive action_category from tool_name prefix convention
        category_map = {
            'log_': 'health', 'read_health': 'health', 'generate_gym': 'health',
            'draft_email': 'communication', 'send_email': 'communication',
            'read_email': 'communication', 'detect_stale': 'communication',
            'read_github': 'projects', 'analyze_commit': 'projects', 'suggest_next': 'projects',
            'read_transaction': 'finance', 'detect_subscription': 'finance',
            'cancel_subscription': 'finance', 'affordability': 'finance',
            'read_document': 'admin', 'extract_document': 'admin', 'draft_reply': 'admin',
        }
        category = 'general'
        for prefix, cat in category_map.items():
            if result.tool_name.startswith(prefix):
                category = cat
                break

        sb.table('audit_trail').insert({
            'user_id': user_id,
            'agent': result.agent,
            'tool_name': result.tool_name,
            'action_category': category,
            'authority_decision': result.decision,
            'executed': executed,
            'execution_time_ms': execution_time_ms,
            'input_data': input_data or {},
            'output_data': output_data or {},
            'error': error,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception:
        pass  # audit logging must never crash the main flow


async def record_approval_outcome(
    user_id: str,
    agent: str,
    tool_name: str,
    approved: bool,
) -> None:
    """Update approval_patterns table — drives auto-approve suggestions."""
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        # Derive action_category from tool_name
        action_category = tool_name.split('_')[0] if '_' in tool_name else tool_name

        existing = sb.table('approval_patterns') \
            .select('*') \
            .eq('user_id', user_id) \
            .eq('agent', agent) \
            .eq('tool_name', tool_name) \
            .maybe_single().execute()

        if existing.data:
            row = existing.data
            updates = {
                'total_approvals': row['total_approvals'] + (1 if approved else 0),
                'total_denials': row['total_denials'] + (0 if approved else 1),
                'consecutive_approvals': row['consecutive_approvals'] + 1 if approved else 0,
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }
            # Suggest auto-approve after 5 consecutive approvals
            if updates['consecutive_approvals'] >= 5 and not row.get('auto_approve'):
                updates['auto_approve'] = True
                updates['auto_approve_set_at'] = datetime.now(timezone.utc).isoformat()

            sb.table('approval_patterns').update(updates) \
                .eq('user_id', user_id).eq('agent', agent).eq('tool_name', tool_name).execute()
        else:
            sb.table('approval_patterns').insert({
                'user_id': user_id,
                'agent': agent,
                'action_category': action_category,
                'tool_name': tool_name,
                'consecutive_approvals': 1 if approved else 0,
                'total_approvals': 1 if approved else 0,
                'total_denials': 0 if approved else 1,
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }).execute()
    except Exception:
        pass
```

- [ ] **Step 3: Create `__init__.py`**

```python
# services/agents/authority/__init__.py
from .engine import check_authority, AuthorityResult
from .audit import log_audit, record_approval_outcome

__all__ = ['check_authority', 'AuthorityResult', 'log_audit', 'record_approval_outcome']
```

- [ ] **Step 4: Add PyYAML to requirements.txt**

Read `services/agents/requirements.txt`, append `pyyaml==6.0.2` and `apscheduler==3.10.4` on new lines.

The file should end with:
```
pyyaml==6.0.2
apscheduler==3.10.4
```

- [ ] **Step 5: Install new dependencies**

```bash
cd C:/Users/Micha/chief/services/agents && .venv/Scripts/activate && pip install pyyaml==6.0.2 apscheduler==3.10.4
```

Expected: Successfully installed pyyaml-6.0.2 apscheduler-3.10.4

- [ ] **Step 6: Verify imports**

```bash
cd C:/Users/Micha/chief/services/agents && .venv/Scripts/activate && python -c "from authority import check_authority; r = check_authority('Pulse', 'log_workout'); print(r.decision)"
```

Expected output: `allowed`

```bash
python -c "from authority import check_authority; r = check_authority('Pulse', 'send_email'); print(r.decision)"
```

Expected output: `denied`

- [ ] **Step 7: Commit**

```bash
git -C C:/Users/Micha/chief add services/agents/authority/ services/agents/requirements.txt
git -C C:/Users/Micha/chief commit -m "feat: add authority engine with audit trail and approval patterns"
git -C C:/Users/Micha/chief push
```

---

## Task 4: Context-aware agents (read real Life Graph data)

**Files:**
- Modify: `services/agents/agents/base.py`
- Modify: `services/agents/agents/pulse.py`
- Modify: `services/agents/agents/echo.py`
- Modify: `services/agents/agents/forge.py`

- [ ] **Step 1: Update BaseAgent to load role YAML and inject context**

Replace `services/agents/agents/base.py`:

```python
# services/agents/agents/base.py
from abc import ABC, abstractmethod
from models import ChatRequest, ChatResponse
import yaml, os


def load_role(agent_name: str) -> dict:
    roles_dir = os.path.join(os.path.dirname(__file__), '..', 'roles')
    path = os.path.join(roles_dir, f'{agent_name.lower()}.yaml')
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return yaml.safe_load(f)


class BaseAgent(ABC):
    name: str
    description: str

    def __init__(self):
        self.role = load_role(self.name)
        self.system_prompt = self.role.get('system_prompt', '').strip()

    @abstractmethod
    async def fetch_context(self, user_id: str) -> str:
        """Fetch relevant Life Graph data for this agent. Returns formatted string."""
        ...

    @abstractmethod
    async def handle(self, request: ChatRequest) -> ChatResponse:
        ...
```

- [ ] **Step 2: Update Pulse agent to read from lg_health**

Replace `services/agents/agents/pulse.py`:

```python
# services/agents/agents/pulse.py
import anthropic
import os
from datetime import datetime, timezone, timedelta
from supabase import create_client
from agents.base import BaseAgent
from models import ChatRequest, ChatResponse

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


class PulseAgent(BaseAgent):
    name = 'Pulse'
    description = 'Health and fitness: recovery, sleep, gym planning, nutrition, weight.'

    async def fetch_context(self, user_id: str) -> str:
        if not user_id:
            return 'No user context available.'
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()

        # Latest recovery
        rec = sb.table('lg_health').select('value, recorded_at') \
            .eq('user_id', user_id).eq('metric', 'recovery') \
            .gte('recorded_at', cutoff) \
            .order('recorded_at', desc=True).limit(1).maybe_single().execute()

        # Latest sleep (last 7)
        sleeps = sb.table('lg_health').select('value, recorded_at') \
            .eq('user_id', user_id).eq('metric', 'sleep') \
            .gte('recorded_at', cutoff) \
            .order('recorded_at', desc=True).limit(7).execute()

        # Recent workouts (last 10)
        workouts = sb.table('lg_health').select('value, recorded_at') \
            .eq('user_id', user_id).eq('metric', 'workout') \
            .gte('recorded_at', cutoff) \
            .order('recorded_at', desc=True).limit(10).execute()

        lines = ['=== HEALTH CONTEXT (last 14 days) ===']

        if rec.data:
            v = rec.data['value']
            lines.append(f'Latest recovery: {v.get("recovery_score", "?")}% '
                         f'(HRV: {v.get("hrv_rmssd_milli", "?")} ms, '
                         f'RHR: {v.get("resting_heart_rate", "?")} bpm) '
                         f'recorded {rec.data["recorded_at"][:10]}')

        if sleeps.data:
            avg_dur = sum(s['value'].get('duration_minutes', 0) for s in sleeps.data) / len(sleeps.data)
            avg_eff = sum(s['value'].get('efficiency_pct', 0) for s in sleeps.data) / len(sleeps.data)
            lines.append(f'Sleep 7-day avg: {avg_dur:.0f} min, efficiency {avg_eff:.1f}%')

        if workouts.data:
            lines.append(f'Workouts in last 14 days: {len(workouts.data)}')
            for w in workouts.data[:3]:
                v = w['value']
                lines.append(f'  - {w["recorded_at"][:10]}: strain {v.get("strain", "?")}, '
                              f'{v.get("duration_minutes", "?")} min, '
                              f'avg HR {v.get("average_heart_rate", "?")} bpm')

        if len(lines) == 1:
            return 'No health data available yet. WHOOP not connected or not synced.'

        return '\n'.join(lines)

    async def handle(self, request: ChatRequest) -> ChatResponse:
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        context = await self.fetch_context(request.user_id or '')
        messages = [{'role': m.role, 'content': m.content} for m in request.history]
        messages.append({'role': 'user', 'content': request.message})

        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=512,
            system=f'{self.system_prompt}\n\n{context}',
            messages=messages,
        )
        return ChatResponse(reply=response.content[0].text, agent='Pulse')
```

- [ ] **Step 3: Update Echo agent to read from lg_communications**

Replace `services/agents/agents/echo.py`:

```python
# services/agents/agents/echo.py
import anthropic
import os
from datetime import datetime, timezone, timedelta
from supabase import create_client
from agents.base import BaseAgent
from models import ChatRequest, ChatResponse

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


class EchoAgent(BaseAgent):
    name = 'Echo'
    description = 'Communication: emails, replies, thread summarization, follow-ups, tone.'

    async def fetch_context(self, user_id: str) -> str:
        if not user_id:
            return 'No user context available.'
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

        # Stale threads (>= 3 days)
        stale = sb.table('lg_communications').select(
            'thread_id, channel, participants, subject, last_message_at, staleness_days'
        ).eq('user_id', user_id).eq('status', 'active') \
         .gte('staleness_days', 3) \
         .order('staleness_days', desc=True).limit(10).execute()

        # Recent threads (last 7 days, for context)
        recent = sb.table('lg_communications').select(
            'subject, channel, participants, last_message_at'
        ).eq('user_id', user_id).eq('status', 'active') \
         .lte('staleness_days', 2) \
         .order('last_message_at', desc=True).limit(5).execute()

        lines = ['=== COMMUNICATION CONTEXT ===']

        if stale.data:
            lines.append(f'STALE THREADS ({len(stale.data)} threads needing attention):')
            for t in stale.data:
                subj = (t.get('subject') or '(no subject)')[:60]
                sender = (t.get('participants') or ['?'])[0][:40]
                lines.append(f'  [{t["staleness_days"]}d] "{subj}" from {sender} via {t["channel"]}')
        else:
            lines.append('No stale threads. Inbox is clear.')

        if recent.data:
            lines.append(f'RECENT ACTIVITY (last 2 days):')
            for t in recent.data:
                subj = (t.get('subject') or '(no subject)')[:60]
                lines.append(f'  "{subj}" — {t["channel"]} — {t["last_message_at"][:10]}')

        return '\n'.join(lines)

    async def handle(self, request: ChatRequest) -> ChatResponse:
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        context = await self.fetch_context(request.user_id or '')
        messages = [{'role': m.role, 'content': m.content} for m in request.history]
        messages.append({'role': 'user', 'content': request.message})

        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=1024,
            system=f'{self.system_prompt}\n\n{context}',
            messages=messages,
        )
        return ChatResponse(reply=response.content[0].text, agent='Echo')
```

- [ ] **Step 4: Update Forge agent to read from lg_projects + lg_health (commits)**

Replace `services/agents/agents/forge.py`:

```python
# services/agents/agents/forge.py
import anthropic
import os
from datetime import datetime, timezone, timedelta
from supabase import create_client
from agents.base import BaseAgent
from models import ChatRequest, ChatResponse

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


class ForgeAgent(BaseAgent):
    name = 'Forge'
    description = 'Projects: thesis, GitHub repos, startup tasks, Notion, deliverables, velocity.'

    async def fetch_context(self, user_id: str) -> str:
        if not user_id:
            return 'No user context available.'
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        cutoff_7d = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        cutoff_30d = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

        # Active projects
        projects = sb.table('lg_projects').select('name, type, status, deadline, tools') \
            .eq('user_id', user_id).eq('status', 'active') \
            .order('updated_at', desc=True).limit(10).execute()

        # Recent commits (last 7 days)
        commits_7d = sb.table('lg_health').select('value, recorded_at') \
            .eq('user_id', user_id).eq('metric', 'github_commit') \
            .gte('recorded_at', cutoff_7d) \
            .order('recorded_at', desc=True).limit(20).execute()

        # Commits in 7-14 days ago (for velocity comparison)
        commits_prev = sb.table('lg_health').select('value, recorded_at') \
            .eq('user_id', user_id).eq('metric', 'github_commit') \
            .lt('recorded_at', cutoff_7d).gte('recorded_at', cutoff_30d).execute()

        lines = ['=== PROJECTS CONTEXT ===']

        if projects.data:
            lines.append(f'ACTIVE PROJECTS ({len(projects.data)}):')
            for p in projects.data:
                deadline_str = f', deadline {p["deadline"]}' if p.get('deadline') else ''
                lines.append(f'  - {p["name"]} ({p["type"]}){deadline_str}')

        if commits_7d.data:
            repos_this_week = set(c['value'].get('repo', '?') for c in commits_7d.data)
            lines.append(f'COMMIT VELOCITY:')
            lines.append(f'  This week: {len(commits_7d.data)} commits across {len(repos_this_week)} repos')
            if commits_prev.data:
                lines.append(f'  Previous period: {len(commits_prev.data)} commits')
                delta = len(commits_7d.data) - len(commits_prev.data)
                trend = f'+{delta}' if delta >= 0 else str(delta)
                lines.append(f'  Trend: {trend} commits vs previous period')
            lines.append('  Recent commits:')
            for c in commits_7d.data[:5]:
                v = c['value']
                msg = v.get('message', '')[:60]
                lines.append(f'    [{v.get("repo", "?")}] {msg} ({c["recorded_at"][:10]})')
        else:
            lines.append('No commits in the last 7 days.')

        return '\n'.join(lines)

    async def handle(self, request: ChatRequest) -> ChatResponse:
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        context = await self.fetch_context(request.user_id or '')
        messages = [{'role': m.role, 'content': m.content} for m in request.history]
        messages.append({'role': 'user', 'content': request.message})

        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=512,
            system=f'{self.system_prompt}\n\n{context}',
            messages=messages,
        )
        return ChatResponse(reply=response.content[0].text, agent='Forge')
```

- [ ] **Step 5: Update models.py to include user_id in ChatRequest**

Read `services/agents/models.py`. The `user_id` field should already be `Optional[str] = None`. Verify it is — if not, add it. The field is needed so agents can call `fetch_context(request.user_id)`.

- [ ] **Step 6: Verify imports**

```bash
cd C:/Users/Micha/chief/services/agents && .venv/Scripts/activate && python -c "from agents.pulse import PulseAgent; from agents.echo import EchoAgent; from agents.forge import ForgeAgent; print('All agents OK')"
```

Expected: `All agents OK`

- [ ] **Step 7: Commit**

```bash
git -C C:/Users/Micha/chief add services/agents/agents/ services/agents/roles/
git -C C:/Users/Micha/chief commit -m "feat: context-aware agents read real Life Graph data + role YAML system prompts"
git -C C:/Users/Micha/chief push
```

---

## Task 5: Momentum Score engine

**Files:**
- Create: `services/agents/scoring/__init__.py`
- Create: `services/agents/scoring/momentum.py`
- Modify: `services/agents/main.py` — add `/score/momentum` endpoint

- [ ] **Step 1: Create momentum scoring module**

Create `services/agents/scoring/__init__.py` (empty):
```python
```

Create `services/agents/scoring/momentum.py`:

```python
# services/agents/scoring/momentum.py
"""
Momentum Score engine.
Scores 5 domains 0-100, writes to momentum_scores table.

Body:  based on recovery %, sleep quality trend, workout consistency
Work:  based on commit velocity, comms staleness, deadline proximity
Money: placeholder until Ledger connectors live (defaults to 50)
Admin: based on pending approval queue items, overdue docs
Discipline: cross-domain consistency meta-score
"""
import os
from datetime import datetime, timezone, timedelta
from supabase import create_client

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


def _clamp(val: float, lo: float = 0, hi: float = 100) -> int:
    return int(max(lo, min(hi, val)))


async def calculate_body_score(sb, user_id: str) -> tuple[int, str]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    rec = sb.table('lg_health').select('value').eq('user_id', user_id) \
        .eq('metric', 'recovery').gte('recorded_at', cutoff) \
        .order('recorded_at', desc=True).limit(1).maybe_single().execute()

    sleeps = sb.table('lg_health').select('value').eq('user_id', user_id) \
        .eq('metric', 'sleep').gte('recorded_at', cutoff).execute()

    workouts_7d = sb.table('lg_health').select('id').eq('user_id', user_id) \
        .eq('metric', 'workout').gte('recorded_at', cutoff).execute()

    score = 50.0
    reason_parts = []

    if rec.data:
        recovery = rec.data['value'].get('recovery_score', 50)
        score = 0.5 * recovery  # recovery is 50% of body score
        reason_parts.append(f'recovery {recovery}%')
    else:
        reason_parts.append('no recovery data')

    if sleeps.data:
        avg_quality = sum(s['value'].get('quality', 50) for s in sleeps.data) / len(sleeps.data)
        score += 0.3 * avg_quality
        reason_parts.append(f'sleep quality {avg_quality:.0f}%')
    else:
        score += 15  # neutral contribution
        reason_parts.append('no sleep data')

    workout_count = len(workouts_7d.data) if workouts_7d.data else 0
    # 4 workouts/week = full points; scale linearly
    workout_contrib = min(workout_count / 4.0, 1.0) * 20
    score += workout_contrib
    reason_parts.append(f'{workout_count} workouts this week')

    return _clamp(score), ', '.join(reason_parts)


async def calculate_work_score(sb, user_id: str) -> tuple[int, str]:
    cutoff_7d = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    reason_parts = []
    score = 50.0

    # Commit velocity
    commits = sb.table('lg_health').select('id').eq('user_id', user_id) \
        .eq('metric', 'github_commit').gte('recorded_at', cutoff_7d).execute()
    commit_count = len(commits.data) if commits.data else 0
    # 10+ commits/week = 40 points; linear
    commit_contrib = min(commit_count / 10.0, 1.0) * 40
    score = commit_contrib
    reason_parts.append(f'{commit_count} commits this week')

    # Comms staleness penalty
    stale = sb.table('lg_communications').select('staleness_days') \
        .eq('user_id', user_id).eq('status', 'active') \
        .gte('staleness_days', 5).execute()
    stale_count = len(stale.data) if stale.data else 0
    staleness_penalty = min(stale_count * 5, 30)  # max 30 point penalty
    score += (60 - staleness_penalty)  # baseline 60 for comms, minus penalty
    reason_parts.append(f'{stale_count} stale threads (≥5 days)')

    return _clamp(score), ', '.join(reason_parts)


async def calculate_admin_score(sb, user_id: str) -> tuple[int, str]:
    pending = sb.table('approval_queue').select('risk_level') \
        .eq('user_id', user_id).eq('status', 'pending').execute()

    pending_count = len(pending.data) if pending.data else 0
    # 0 pending = 100; each pending item costs 10 points
    score = max(0, 100 - pending_count * 10)
    return _clamp(score), f'{pending_count} items pending approval'


async def calculate_momentum(user_id: str) -> dict:
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    body_score, body_reason = await calculate_body_score(sb, user_id)
    work_score, work_reason = await calculate_work_score(sb, user_id)
    admin_score, admin_reason = await calculate_admin_score(sb, user_id)
    money_score = 50  # placeholder until Ledger connectors live
    discipline_score = _clamp((body_score + work_score + admin_score + money_score) / 4)
    total = _clamp((body_score * 0.25 + work_score * 0.3 + money_score * 0.2
                    + admin_score * 0.15 + discipline_score * 0.1))

    scored_at = datetime.now(timezone.utc).isoformat()

    sb.table('momentum_scores').insert({
        'user_id': user_id,
        'total': total,
        'body': body_score,
        'money': money_score,
        'work': work_score,
        'admin': admin_score,
        'discipline': discipline_score,
        'scored_at': scored_at,
    }).execute()

    return {
        'total': total,
        'body': body_score,
        'money': money_score,
        'work': work_score,
        'admin': admin_score,
        'discipline': discipline_score,
        'reasons': {
            'body': body_reason,
            'work': work_reason,
            'admin': admin_reason,
        },
        'scored_at': scored_at,
    }
```

- [ ] **Step 2: Add `/score/momentum` endpoint to main.py**

Read `services/agents/main.py`. Add this import at the top (after existing imports):

```python
from scoring.momentum import calculate_momentum
```

Add this endpoint after the existing sync endpoints:

```python
@app.post('/score/momentum')
async def score_momentum(req: SyncRequest):
    result = await calculate_momentum(req.user_id)
    return result
```

- [ ] **Step 3: Verify module imports**

```bash
cd C:/Users/Micha/chief/services/agents && .venv/Scripts/activate && python -c "from scoring.momentum import calculate_momentum; print('Momentum OK')"
```

Expected: `Momentum OK`

- [ ] **Step 4: Commit**

```bash
git -C C:/Users/Micha/chief add services/agents/scoring/ services/agents/main.py
git -C C:/Users/Micha/chief commit -m "feat: momentum score engine with real data from Life Graph"
git -C C:/Users/Micha/chief push
```

---

## Task 6: Morning Brief generator

**Files:**
- Create: `services/agents/brief/__init__.py`
- Create: `services/agents/brief/generator.py`
- Modify: `services/agents/main.py` — add `/brief/generate` endpoint

- [ ] **Step 1: Create brief generator**

Create `services/agents/brief/__init__.py` (empty).

Create `services/agents/brief/generator.py`:

```python
# services/agents/brief/generator.py
"""
Generates a structured Morning Brief from all Life Graph data.
Uses Claude to synthesize health + comms + projects + admin into
a structured JSON brief, then stores it in the briefs table.
"""
import anthropic
import json
import os
from datetime import datetime, timezone, timedelta
from supabase import create_client
from scoring.momentum import calculate_momentum

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

BRIEF_PROMPT = """You are Chief, a personal life operating system. Generate a structured Morning Brief
for the user based on the Life Graph data provided. 

Return ONLY valid JSON matching this exact schema — no markdown, no prose outside the JSON:
{
  "greeting": "Good morning, [name].",
  "sections": [
    {
      "domain": "body",
      "agent": "Pulse",
      "status": "ok|med|high|crit",
      "headline": "Recovery 72% · Sleep 6h 20m",
      "detail": "Slightly below target. Skip heavy compounds today.",
      "action": "Upper accessories recommended"
    }
  ],
  "life_debt": {
    "total": 5,
    "items": [
      {"domain": "communication", "count": 3, "description": "3 stale emails (2 high priority)"}
    ]
  },
  "best_move": "Send thesis progress update. Your professor email is 5 days old.",
  "patterns": ["Late-night UberEats correlates with lower sleep quality"]
}

Rules:
- Include a section for each domain with data: body (if WHOOP data), work (if commits/comms), admin (if queue items)
- Status: ok = good, med = needs attention, high = urgent, crit = critical
- Life debt: count ALL unresolved items across domains
- Best move: the single highest-impact action for today
- Patterns: cross-domain correlations you notice (only if data supports it — no made-up correlations)
- Be specific: use real numbers, real names, real dates from the data
- Voice: warm, direct, like a mentor — not robotic"""


async def gather_brief_context(sb, user_id: str) -> str:
    """Gather all Life Graph data for brief generation."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    parts = []

    # Health
    rec = sb.table('lg_health').select('value, recorded_at').eq('user_id', user_id) \
        .eq('metric', 'recovery').gte('recorded_at', cutoff) \
        .order('recorded_at', desc=True).limit(1).maybe_single().execute()

    sleep7 = sb.table('lg_health').select('value').eq('user_id', user_id) \
        .eq('metric', 'sleep').gte('recorded_at', cutoff).execute()

    workouts = sb.table('lg_health').select('value, recorded_at').eq('user_id', user_id) \
        .eq('metric', 'workout').gte('recorded_at', cutoff) \
        .order('recorded_at', desc=True).limit(5).execute()

    if rec.data:
        v = rec.data['value']
        parts.append(f'HEALTH: recovery={v.get("recovery_score")}%, '
                     f'HRV={v.get("hrv_rmssd_milli")}ms, '
                     f'RHR={v.get("resting_heart_rate")}bpm '
                     f'(as of {rec.data["recorded_at"][:10]})')

    if sleep7.data:
        avg_min = sum(s['value'].get('duration_minutes', 0) for s in sleep7.data) / len(sleep7.data)
        parts.append(f'SLEEP 7d avg: {avg_min:.0f} min ({avg_min/60:.1f}h)')

    if workouts.data:
        parts.append(f'WORKOUTS this week: {len(workouts.data)}')

    # Communications
    stale = sb.table('lg_communications').select('subject, channel, staleness_days, participants') \
        .eq('user_id', user_id).eq('status', 'active') \
        .gte('staleness_days', 3).order('staleness_days', desc=True).limit(5).execute()

    if stale.data:
        parts.append(f'STALE COMMS ({len(stale.data)} threads):')
        for t in stale.data:
            subj = (t.get('subject') or '(no subject)')[:50]
            parts.append(f'  [{t["staleness_days"]}d] "{subj}" via {t["channel"]}')

    # Projects
    commits = sb.table('lg_health').select('value, recorded_at').eq('user_id', user_id) \
        .eq('metric', 'github_commit').gte('recorded_at', cutoff) \
        .order('recorded_at', desc=True).limit(10).execute()

    if commits.data:
        repos = set(c['value'].get('repo', '?') for c in commits.data)
        parts.append(f'COMMITS this week: {len(commits.data)} across {len(repos)} repos')

    # Approval queue
    queue = sb.table('approval_queue').select('title, agent, risk_level').eq('user_id', user_id) \
        .eq('status', 'pending').order('created_at', desc=True).limit(5).execute()

    if queue.data:
        parts.append(f'APPROVAL QUEUE ({len(queue.data)} items):')
        for q in queue.data:
            parts.append(f'  [{q["risk_level"]}] {q["title"]} [{q["agent"]}]')

    return '\n'.join(parts) if parts else 'No Life Graph data available yet.'


async def generate_morning_brief(user_id: str, user_name: str = 'there') -> dict:
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    context = await gather_brief_context(sb, user_id)
    today = datetime.now(timezone.utc).date().isoformat()

    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    response = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=1500,
        system=BRIEF_PROMPT,
        messages=[{
            'role': 'user',
            'content': f'User name: {user_name}\nToday: {today}\n\nLife Graph data:\n{context}'
        }],
    )

    raw = response.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith('```'):
        raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()

    try:
        brief_data = json.loads(raw)
    except json.JSONDecodeError:
        brief_data = {
            'greeting': f'Good morning, {user_name}.',
            'sections': [],
            'life_debt': {'total': 0, 'items': []},
            'best_move': 'Check your connectors — data is still syncing.',
            'patterns': [],
        }

    # Store in briefs table (upsert by date + type)
    sb.table('briefs').upsert({
        'user_id': user_id,
        'brief_date': today,
        'type': 'morning',
        'greeting': brief_data.get('greeting', ''),
        'sections': brief_data.get('sections', []),
        'life_debt': brief_data.get('life_debt', {'total': 0, 'items': []}),
        'generated_by': 'claude',
        'model': 'claude-sonnet-4-6',
        'created_at': datetime.now(timezone.utc).isoformat(),
    }, on_conflict='user_id,brief_date,type').execute()

    # Store goal_check_in record
    sb.table('goal_check_ins').insert({
        'user_id': user_id,
        'type': 'morning_plan',
        'highlights': [],
        'actions_planned': [brief_data.get('best_move', '')] if brief_data.get('best_move') else [],
        'narrative': brief_data.get('best_move', ''),
        'created_at': datetime.now(timezone.utc).isoformat(),
    }).execute()

    return brief_data
```

- [ ] **Step 2: Add `/brief/generate` endpoint to main.py**

Read `services/agents/main.py`. Add this import after existing imports:

```python
from brief.generator import generate_morning_brief
```

Add a new Pydantic model after `SyncRequest`:

```python
class BriefRequest(BaseModel):
    user_id: str
    user_name: str = 'there'
```

Add this endpoint after the momentum endpoint:

```python
@app.post('/brief/generate')
async def generate_brief(req: BriefRequest):
    result = await generate_morning_brief(req.user_id, req.user_name)
    return result
```

- [ ] **Step 3: Verify imports**

```bash
cd C:/Users/Micha/chief/services/agents && .venv/Scripts/activate && python -c "from brief.generator import generate_morning_brief; print('Brief generator OK')"
```

Expected: `Brief generator OK`

- [ ] **Step 4: Commit**

```bash
git -C C:/Users/Micha/chief add services/agents/brief/ services/agents/main.py
git -C C:/Users/Micha/chief commit -m "feat: AI Morning Brief generator reads Life Graph, writes to briefs table"
git -C C:/Users/Micha/chief push
```

---

## Task 7: Frontend — Today page reads from briefs table

**Files:**
- Modify: `apps/web/app/(app)/today/page.tsx`
- Modify: `apps/web/app/api/chat/route.ts` — pass user_id to agent service
- Modify: `apps/web/components/today/MorningBriefReal.tsx`
- Modify: `apps/web/components/today/ApprovalQueue.tsx`
- Create: `apps/web/components/today/LifeDebt.tsx`
- Modify: `apps/web/app/api/connectors/google/callback/route.ts` — trigger brief generation after sync

- [ ] **Step 1: Update /api/chat to pass user_id**

Read `apps/web/app/api/chat/route.ts`. Replace with:

```ts
// apps/web/app/api/chat/route.ts
import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function POST(request: Request) {
  const body = await request.json();
  const agentServiceUrl = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8001';

  // Attach user_id so agents can load Life Graph context
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  const enrichedBody = { ...body, user_id: user?.id ?? null };

  try {
    const res = await fetch(`${agentServiceUrl}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(enrichedBody),
    });
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({
      reply: "Hey — I'm Chief. The agent service is starting up. Try again in a moment.",
      agent: 'Chief',
    });
  }
}
```

- [ ] **Step 2: Create LifeDebt component**

Create `apps/web/components/today/LifeDebt.tsx`:

```tsx
// apps/web/components/today/LifeDebt.tsx
import { Panel } from '@/components/design-system';
import { AlertCircle } from 'lucide-react';

interface DebtItem {
  domain: string;
  count: number;
  description: string;
}

interface LifeDebtProps {
  total: number;
  items: DebtItem[];
}

const DOMAIN_COLORS: Record<string, string> = {
  communication: 'text-[var(--v2-violet)]',
  financial:     'text-[var(--v2-warn)]',
  health:        'text-[var(--v2-teal)]',
  admin:         'text-[var(--v2-info)]',
  work:          'text-[var(--v2-ok)]',
};

export function LifeDebt({ total, items }: LifeDebtProps) {
  if (total === 0) return null;

  return (
    <Panel variant="inset" className="p-4 space-y-3">
      <div className="flex items-center gap-2">
        <AlertCircle size={14} className="text-[var(--v2-warn)]" />
        <span className="text-[12px] font-semibold uppercase tracking-[0.08em] text-[var(--v2-warn)]">
          Life Debt — {total} item{total !== 1 ? 's' : ''}
        </span>
      </div>
      <div className="space-y-1.5">
        {items.map((item, i) => (
          <div key={i} className="flex items-start gap-2">
            <span className={`text-[11px] font-semibold uppercase tracking-wider mt-0.5 ${DOMAIN_COLORS[item.domain] ?? 'text-[var(--v2-muted)]'}`}>
              {item.domain}
            </span>
            <span className="text-[12px] text-[var(--v2-text-dim)]">{item.description}</span>
          </div>
        ))}
      </div>
      <p className="text-[11px] text-[var(--v2-subtle)] italic">
        Want to clear 3 today? Ask Chief to pick the highest-impact ones.
      </p>
    </Panel>
  );
}
```

- [ ] **Step 3: Update MorningBriefReal to accept AI-generated sections**

Replace `apps/web/components/today/MorningBriefReal.tsx`:

```tsx
// apps/web/components/today/MorningBriefReal.tsx
import { Panel, StatusDot } from '@/components/design-system';
import { Activity, Briefcase, FileText, DollarSign, ArrowRight } from 'lucide-react';

type BriefStatus = 'ok' | 'med' | 'high' | 'crit';

export interface AiBriefSection {
  domain: string;
  agent: string;
  status: BriefStatus;
  headline: string;
  detail: string;
  action?: string;
}

interface MorningBriefRealProps {
  greeting: string;
  sections: AiBriefSection[];
  bestMove?: string;
  patterns?: string[];
}

const DOMAIN_ICONS: Record<string, React.ElementType> = {
  body:  Activity,
  work:  Briefcase,
  admin: FileText,
  money: DollarSign,
};

export function MorningBriefReal({ greeting, sections, bestMove, patterns }: MorningBriefRealProps) {
  if (sections.length === 0) {
    return (
      <div className="text-[13px] text-[var(--v2-muted)]">
        Syncing your data… check back in a moment.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-[var(--v2-text)]">{greeting}</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {sections.map((s, i) => {
          const Icon = DOMAIN_ICONS[s.domain] ?? Activity;
          return (
            <Panel key={i} className="p-4 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Icon size={14} className="text-[var(--v2-violet)]" />
                  <span className="text-[11px] uppercase tracking-[0.08em] font-semibold text-[var(--v2-muted)]">
                    {s.domain}
                  </span>
                  <span className="text-[10px] text-[var(--v2-subtle)]">[{s.agent}]</span>
                </div>
                <StatusDot severity={s.status as any} size="xs" />
              </div>
              <p className="text-sm font-medium text-[var(--v2-text)]">{s.headline}</p>
              <p className="text-[12px] text-[var(--v2-muted)]">{s.detail}</p>
              {s.action && (
                <p className="text-[12px] text-[var(--v2-violet)] flex items-center gap-1">
                  <ArrowRight size={11} />
                  {s.action}
                </p>
              )}
            </Panel>
          );
        })}
      </div>

      {bestMove && (
        <Panel variant="elevated" className="p-4">
          <div className="flex items-start gap-3">
            <div className="w-1.5 h-full min-h-[20px] rounded-full bg-[var(--v2-violet)] flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-muted)] mb-1">Today's best move</p>
              <p className="text-sm text-[var(--v2-text)]">{bestMove}</p>
            </div>
          </div>
        </Panel>
      )}

      {patterns && patterns.length > 0 && (
        <div className="space-y-1">
          <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-subtle)]">Patterns Chief noticed</p>
          {patterns.map((p, i) => (
            <p key={i} className="text-[12px] text-[var(--v2-muted)] italic">{p}</p>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Rewrite today/page.tsx to read from briefs table**

Replace `apps/web/app/(app)/today/page.tsx`:

```tsx
// apps/web/app/(app)/today/page.tsx
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { TopBar } from '@/components/layout/TopBar';
import { ConnectGate } from '@/components/today/ConnectGate';
import { MorningBriefReal, type AiBriefSection } from '@/components/today/MorningBriefReal';
import { MomentumScore } from '@/components/today/MomentumScore';
import { ApprovalQueueServer } from '@/components/today/ApprovalQueueServer';
import { LifeDebt } from '@/components/today/LifeDebt';

export default async function TodayPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect('/login');

  // Gate: at least one connector must be live
  const { data: tokens } = await supabase
    .from('connector_tokens')
    .select('connector, sync_status')
    .eq('user_id', user.id)
    .in('sync_status', ['ok', 'syncing']);

  const hasLiveConnector = (tokens ?? []).length > 0;

  // Latest momentum score
  const { data: scoreRow } = await supabase
    .from('momentum_scores')
    .select('*')
    .eq('user_id', user.id)
    .order('scored_at', { ascending: false })
    .limit(1)
    .maybeSingle();

  // Latest AI-generated brief for today
  const today = new Date().toISOString().slice(0, 10);
  const { data: brief } = await supabase
    .from('briefs')
    .select('*')
    .eq('user_id', user.id)
    .eq('brief_date', today)
    .eq('type', 'morning')
    .maybeSingle();

  // Pending approval queue
  const { data: queueItems } = await supabase
    .from('approval_queue')
    .select('id, agent, title, description, risk_level')
    .eq('user_id', user.id)
    .eq('status', 'pending')
    .order('created_at', { ascending: false })
    .limit(10);

  const domains = scoreRow ? [
    { label: 'Body',       value: scoreRow.body ?? 0,       color: '#18E6D8' },
    { label: 'Money',      value: scoreRow.money ?? 0,      color: '#F7A93B' },
    { label: 'Work',       value: scoreRow.work ?? 0,       color: '#8A3AFF' },
    { label: 'Admin',      value: scoreRow.admin ?? 0,      color: '#38F2A8' },
    { label: 'Discipline', value: scoreRow.discipline ?? 0, color: '#3B82F6' },
  ] : [];

  const greeting = brief?.greeting ?? (() => {
    const hour = new Date().getHours();
    return hour < 12 ? 'Good morning.' : hour < 18 ? 'Good afternoon.' : 'Good evening.';
  })();

  const sections: AiBriefSection[] = (brief?.sections as AiBriefSection[]) ?? [];
  const lifeDebt = brief?.life_debt as { total: number; items: { domain: string; count: number; description: string }[] } | null;
  const bestMove = (brief as any)?.best_move as string | undefined;
  const patterns = (brief as any)?.patterns as string[] | undefined;

  return (
    <>
      <TopBar title="Today" momentumScore={scoreRow?.total} />
      <main className="flex-1 overflow-y-auto p-4 max-w-3xl">
        {!hasLiveConnector ? (
          <ConnectGate />
        ) : (
          <div className="space-y-5">
            {scoreRow && <MomentumScore total={scoreRow.total} domains={domains} />}
            {lifeDebt && lifeDebt.total > 0 && (
              <LifeDebt total={lifeDebt.total} items={lifeDebt.items} />
            )}
            <MorningBriefReal
              greeting={greeting}
              sections={sections}
              bestMove={bestMove}
              patterns={patterns}
            />
            <ApprovalQueueServer items={queueItems ?? []} />
          </div>
        )}
      </main>
    </>
  );
}
```

- [ ] **Step 5: Add brief regeneration trigger to Google callback**

Read `apps/web/app/api/connectors/google/callback/route.ts`. After the existing sync trigger, add:

```ts
// After the existing sync trigger line, add:
fetch(`${agentUrl}/brief/generate`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ user_id: user.id, user_name: userInfo.given_name ?? 'there' }),
}).catch(() => {});
```

- [ ] **Step 6: TypeScript check**

```bash
cd C:/Users/Micha/chief/apps/web && npx tsc --noEmit 2>&1 | grep "error TS" | head -10
```

Fix any TypeScript errors in the new/modified files.

- [ ] **Step 7: Commit**

```bash
git -C C:/Users/Micha/chief add apps/web/
git -C C:/Users/Micha/chief commit -m "feat: Today page reads AI-generated brief from briefs table, adds LifeDebt panel"
git -C C:/Users/Micha/chief push
```

---

## Task 8: Approval queue — context capsules + auto-approve badge

**Files:**
- Modify: `apps/web/components/today/ApprovalQueue.tsx`
- Modify: `apps/web/app/api/queue/approve/route.ts` — call record_approval_outcome

- [ ] **Step 1: Update ApprovalQueue to show context capsule and auto-approve badge**

Replace `apps/web/components/today/ApprovalQueue.tsx`:

```tsx
// apps/web/components/today/ApprovalQueue.tsx
'use client';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Panel, Button, StatusDot } from '@/components/design-system';
import { CheckCircle, XCircle, ChevronDown, Zap } from 'lucide-react';

export interface QueueItem {
  id: string;
  agent: string;
  title: string;
  description: string;
  riskLevel: 'auto' | 'notify' | 'approve' | 'confirm';
  contextCapsule?: {
    sources?: string[];
    reasoning?: string;
    confidence?: 'HIGH' | 'MEDIUM' | 'LOW';
  };
  autoApproveSuggested?: boolean;
}

interface ApprovalQueueProps {
  items: QueueItem[];
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  onEnableAutoApprove?: (id: string) => void;
}

const RISK_SEVERITY: Record<QueueItem['riskLevel'], 'ok' | 'info' | 'med' | 'high'> = {
  auto:    'ok',
  notify:  'info',
  approve: 'med',
  confirm: 'high',
};

const RISK_LABELS: Record<QueueItem['riskLevel'], string> = {
  auto:    'auto',
  notify:  'notify',
  approve: 'approval',
  confirm: 'confirm',
};

export function ApprovalQueue({ items, onApprove, onReject, onEnableAutoApprove }: ApprovalQueueProps) {
  const [expanded, setExpanded] = useState<string | null>(null);

  if (items.length === 0) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-[12px] uppercase tracking-[0.08em] font-semibold text-[var(--v2-muted)]">
        Queue — {items.length} item{items.length !== 1 ? 's' : ''}
      </h3>
      <AnimatePresence initial={false}>
        {items.map(item => (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, x: 40, transition: { duration: 0.2 } }}
            transition={{ duration: 0.25 }}
          >
            <Panel className="p-3 space-y-2">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-2 flex-1 min-w-0">
                  <StatusDot severity={RISK_SEVERITY[item.riskLevel]} size="xs" className="mt-1 flex-shrink-0" />
                  <div className="min-w-0 space-y-0.5">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium text-[var(--v2-text)] truncate">{item.title}</span>
                      <span className="text-[10px] text-[var(--v2-subtle)] flex-shrink-0">[{item.agent}]</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded-[4px] bg-[rgba(247,240,255,0.06)] text-[var(--v2-subtle)]">
                        {RISK_LABELS[item.riskLevel]}
                      </span>
                      {item.autoApproveSuggested && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-[4px] bg-[rgba(56,242,168,0.10)] text-[var(--v2-ok)] flex items-center gap-1">
                          <Zap size={9} />
                          auto-approve available
                        </span>
                      )}
                    </div>
                    {item.description && (
                      <p className="text-[12px] text-[var(--v2-muted)]">{item.description}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  {item.contextCapsule && (
                    <Button
                      variant="ghost"
                      size="xs"
                      onClick={() => setExpanded(expanded === item.id ? null : item.id)}
                    >
                      <ChevronDown
                        size={12}
                        className={expanded === item.id ? 'rotate-180 transition-transform' : 'transition-transform'}
                      />
                    </Button>
                  )}
                  <Button variant="ghost" size="xs" onClick={() => onReject(item.id)}>
                    <XCircle size={13} className="text-[var(--v2-crit)]" />
                  </Button>
                  <Button variant="solid" size="xs" onClick={() => onApprove(item.id)}>
                    <CheckCircle size={13} />
                    Approve
                  </Button>
                </div>
              </div>

              {expanded === item.id && item.contextCapsule && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="border-t border-[var(--v2-border)] pt-2 space-y-1.5"
                >
                  <p className="text-[10px] uppercase tracking-[0.08em] text-[var(--v2-subtle)]">Context capsule</p>
                  {item.contextCapsule.sources && item.contextCapsule.sources.length > 0 && (
                    <div className="space-y-0.5">
                      {item.contextCapsule.sources.map((s, i) => (
                        <p key={i} className="text-[11px] text-[var(--v2-muted)] font-mono">├─ {s}</p>
                      ))}
                    </div>
                  )}
                  {item.contextCapsule.reasoning && (
                    <p className="text-[12px] text-[var(--v2-text-dim)]">{item.contextCapsule.reasoning}</p>
                  )}
                  {item.contextCapsule.confidence && (
                    <p className="text-[11px] text-[var(--v2-subtle)]">
                      Confidence: <span className="text-[var(--v2-text-dim)]">{item.contextCapsule.confidence}</span>
                    </p>
                  )}
                  {item.autoApproveSuggested && onEnableAutoApprove && (
                    <Button variant="outline" size="xs" onClick={() => onEnableAutoApprove(item.id)}>
                      <Zap size={10} />
                      Enable auto-approve for this action
                    </Button>
                  )}
                </motion.div>
              )}
            </Panel>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
```

- [ ] **Step 2: Update ApprovalQueueServer to map context_capsule and auto_approve**

Replace `apps/web/components/today/ApprovalQueueServer.tsx`:

```tsx
// apps/web/components/today/ApprovalQueueServer.tsx
'use client';
import { useState } from 'react';
import { ApprovalQueue, type QueueItem } from './ApprovalQueue';
import { toast } from 'sonner';

interface QueueRow {
  id: string;
  agent: string;
  title: string;
  description: string | null;
  risk_level: 'auto' | 'notify' | 'approve' | 'confirm';
  context_capsule: Record<string, unknown> | null;
}

function mapRow(i: QueueRow): QueueItem {
  const capsule = i.context_capsule as any;
  return {
    id: i.id,
    agent: i.agent,
    title: i.title,
    description: i.description ?? '',
    riskLevel: i.risk_level,
    contextCapsule: capsule ? {
      sources: capsule.sources ?? [],
      reasoning: capsule.reasoning ?? '',
      confidence: capsule.confidence ?? 'MEDIUM',
    } : undefined,
    autoApproveSuggested: capsule?.auto_approve_suggested ?? false,
  };
}

export function ApprovalQueueServer({ items }: { items: QueueRow[] }) {
  const [localItems, setLocalItems] = useState<QueueItem[]>(items.map(mapRow));

  async function handleApprove(id: string) {
    const item = localItems.find(i => i.id === id);
    setLocalItems(prev => prev.filter(i => i.id !== id));
    await fetch('/api/queue/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id }),
    });
    toast.success(`Approved: ${item?.title}`);
  }

  async function handleReject(id: string) {
    const item = localItems.find(i => i.id === id);
    setLocalItems(prev => prev.filter(i => i.id !== id));
    await fetch('/api/queue/reject', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id }),
    });
    toast(`Skipped: ${item?.title}`);
  }

  async function handleAutoApprove(id: string) {
    const item = localItems.find(i => i.id === id);
    await fetch('/api/queue/auto-approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, agent: item?.agent }),
    });
    toast.success('Auto-approve enabled for this action type.');
  }

  return (
    <ApprovalQueue
      items={localItems}
      onApprove={handleApprove}
      onReject={handleReject}
      onEnableAutoApprove={handleAutoApprove}
    />
  );
}
```

- [ ] **Step 3: Add /api/queue/auto-approve route**

Create `apps/web/app/api/queue/auto-approve/route.ts`:

```ts
import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function POST(request: Request) {
  const { id } = await request.json();
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  // Get the queue item to know agent + action_type
  const { data: item } = await supabase
    .from('approval_queue')
    .select('agent, action_type')
    .eq('id', id)
    .eq('user_id', user.id)
    .maybeSingle();

  if (item) {
    // Upsert approval_pattern with auto_approve=true
    await supabase.from('approval_patterns').upsert({
      user_id: user.id,
      agent: item.agent,
      action_category: item.action_type.split('_')[0],
      tool_name: item.action_type,
      auto_approve: true,
      auto_approve_set_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }, { onConflict: 'user_id,agent,tool_name' });
  }

  return NextResponse.json({ ok: true });
}
```

- [ ] **Step 4: Run TypeScript check**

```bash
cd C:/Users/Micha/chief/apps/web && npx tsc --noEmit 2>&1 | grep "error TS" | head -10
```

Fix any type errors.

- [ ] **Step 5: Commit**

```bash
git -C C:/Users/Micha/chief add apps/web/
git -C C:/Users/Micha/chief commit -m "feat: approval queue with context capsules, auto-approve badge, and /api/queue/auto-approve"
git -C C:/Users/Micha/chief push
```

---

## Task 9: Gmail connector — extract People entities

**Files:**
- Modify: `services/agents/connectors/gmail.py`

- [ ] **Step 1: Update gmail.py to extract People entities from senders**

After the `sync_gmail` function, inside the thread-processing loop, add entity extraction. Read the current `services/agents/connectors/gmail.py` and add this helper function before `sync_gmail`:

```python
import re

def _extract_email_name(from_header: str) -> tuple[str, str]:
    """Parse 'Name <email@domain.com>' or 'email@domain.com' into (name, email)."""
    match = re.match(r'^"?([^"<]+?)"?\s*<([^>]+)>', from_header.strip())
    if match:
        return match.group(1).strip(), match.group(2).strip()
    email = from_header.strip()
    name = email.split('@')[0].replace('.', ' ').title()
    return name, email


def _upsert_person_entity(sb, user_id: str, name: str, email: str, source: str):
    """Upsert a Person entity in the entities table."""
    try:
        sb.table('entities').upsert({
            'user_id': user_id,
            'type': 'person',
            'name': name,
            'properties': {'email': email},
            'source': source,
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }, on_conflict='user_id,type,name').execute()
    except Exception:
        pass  # entity extraction must not crash the sync
```

Then inside the thread processing loop, after extracting `from_addr`, add:

```python
            # Extract and store Person entity
            person_name, person_email = _extract_email_name(from_addr)
            if person_email and '@' in person_email:
                _upsert_person_entity(sb, user_id, person_name, person_email, 'gmail')
```

- [ ] **Step 2: Verify import**

```bash
cd C:/Users/Micha/chief/services/agents && .venv/Scripts/activate && python -c "from connectors.gmail import sync_gmail; print('Gmail OK')"
```

Expected: `Gmail OK`

- [ ] **Step 3: Commit**

```bash
git -C C:/Users/Micha/chief add services/agents/connectors/gmail.py
git -C C:/Users/Micha/chief commit -m "feat: Gmail sync extracts Person entities into knowledge graph"
git -C C:/Users/Micha/chief push
```

---

## Task 10: Weekly Replay page

**Files:**
- Create: `apps/web/app/(app)/replay/page.tsx`
- Create: `apps/web/components/replay/WeeklyReplay.tsx`

- [ ] **Step 1: Create WeeklyReplay component**

Create `apps/web/components/replay/WeeklyReplay.tsx`:

```tsx
// apps/web/components/replay/WeeklyReplay.tsx
import { Panel } from '@/components/design-system';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface CheckIn {
  id: string;
  type: string;
  narrative: string | null;
  highlights: string[] | null;
  lowlights: string[] | null;
  patterns_noticed: string[] | null;
  momentum_start: number | null;
  momentum_end: number | null;
  actions_planned: string[] | null;
  actions_completed: string[] | null;
  created_at: string;
}

interface WeeklyReplayProps {
  checkIns: CheckIn[];
  currentScore: number | null;
}

export function WeeklyReplay({ checkIns, currentScore }: WeeklyReplayProps) {
  if (checkIns.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center space-y-3">
        <p className="text-sm font-medium text-[var(--v2-text)]">No replays yet.</p>
        <p className="text-[13px] text-[var(--v2-muted)] max-w-xs">
          Your Weekly Replay appears here after Chief generates your first Morning Brief.
          Connect Gmail to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {checkIns.map(ci => {
        const delta = (ci.momentum_end ?? 0) - (ci.momentum_start ?? 0);
        const TrendIcon = delta > 0 ? TrendingUp : delta < 0 ? TrendingDown : Minus;
        const trendColor = delta > 0 ? 'text-[var(--v2-ok)]' : delta < 0 ? 'text-[var(--v2-crit)]' : 'text-[var(--v2-muted)]';
        const date = new Date(ci.created_at).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });

        return (
          <Panel key={ci.id} className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[12px] uppercase tracking-[0.08em] text-[var(--v2-muted)]">{date}</span>
              {(ci.momentum_start || ci.momentum_end) && (
                <div className={`flex items-center gap-1.5 text-[12px] font-semibold ${trendColor}`}>
                  <TrendIcon size={13} />
                  {ci.momentum_start} → {ci.momentum_end}
                  {delta !== 0 && <span>({delta > 0 ? '+' : ''}{delta})</span>}
                </div>
              )}
            </div>

            {ci.narrative && (
              <p className="text-sm text-[var(--v2-text-dim)] leading-relaxed">{ci.narrative}</p>
            )}

            {ci.highlights && ci.highlights.length > 0 && (
              <div className="space-y-1">
                <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-ok)]">Highlights</p>
                {ci.highlights.map((h, i) => (
                  <p key={i} className="text-[12px] text-[var(--v2-muted)]">• {h}</p>
                ))}
              </div>
            )}

            {ci.lowlights && ci.lowlights.length > 0 && (
              <div className="space-y-1">
                <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-crit)]">Lowlights</p>
                {ci.lowlights.map((l, i) => (
                  <p key={i} className="text-[12px] text-[var(--v2-muted)]">• {l}</p>
                ))}
              </div>
            )}

            {ci.patterns_noticed && ci.patterns_noticed.length > 0 && (
              <div className="space-y-1">
                <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-violet)]">Patterns noticed</p>
                {ci.patterns_noticed.map((p, i) => (
                  <p key={i} className="text-[12px] text-[var(--v2-muted)] italic">{p}</p>
                ))}
              </div>
            )}
          </Panel>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Create replay page**

Create `apps/web/app/(app)/replay/page.tsx`:

```tsx
// apps/web/app/(app)/replay/page.tsx
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { TopBar } from '@/components/layout/TopBar';
import { WeeklyReplay } from '@/components/replay/WeeklyReplay';

export default async function ReplayPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect('/login');

  const { data: checkIns } = await supabase
    .from('goal_check_ins')
    .select('*')
    .eq('user_id', user.id)
    .order('created_at', { ascending: false })
    .limit(20);

  const { data: scoreRow } = await supabase
    .from('momentum_scores')
    .select('total')
    .eq('user_id', user.id)
    .order('scored_at', { ascending: false })
    .limit(1)
    .maybeSingle();

  return (
    <>
      <TopBar title="Replay" />
      <main className="flex-1 overflow-y-auto p-4 max-w-2xl">
        <WeeklyReplay checkIns={checkIns ?? []} currentScore={scoreRow?.total ?? null} />
      </main>
    </>
  );
}
```

- [ ] **Step 3: TypeScript check and commit**

```bash
cd C:/Users/Micha/chief/apps/web && npx tsc --noEmit 2>&1 | grep "error TS" | head -10
```

Fix any errors.

```bash
git -C C:/Users/Micha/chief add apps/web/
git -C C:/Users/Micha/chief commit -m "feat: Replay page with goal check-ins and weekly narrative"
git -C C:/Users/Micha/chief push
```

---

## Self-Review

**Spec coverage:**
- ✅ Morning Brief generation (Task 6 — brief/generator.py + Claude)
- ✅ Momentum Score engine (Task 5 — scoring/momentum.py)
- ✅ Authority engine (Task 3 — authority/engine.py + audit.py)
- ✅ Role YAML configs for all 5 agents (Task 2)
- ✅ Agents read real Life Graph data (Task 4 — Pulse/Echo/Forge context)
- ✅ audit_trail + approval_patterns tables (Task 1, migration 0003)
- ✅ briefs + goal_check_ins tables (Task 1, migration 0004)
- ✅ entities/facts/relationships tables (Task 1, migration 0005)
- ✅ Context capsules on approval queue items (Task 8)
- ✅ Auto-approve suggestion badge (Task 8)
- ✅ Life Debt panel (Task 7 — LifeDebt.tsx)
- ✅ Best move + patterns in Morning Brief (Task 7 — MorningBriefReal.tsx)
- ✅ Today page reads from briefs table (Task 7)
- ✅ Gmail entity extraction (Task 9)
- ✅ Weekly Replay page (Task 10)
- ✅ user_id passed to agents for context (Task 7, /api/chat)
- ✅ Migrations pushed via GitHub to trigger Supabase auto-apply (Task 1)

**Not in Phase 1A (deferred to 1B):**
- Voice capture (Deepgram STT → Claude intent → Life Graph)
- ElevenLabs TTS
- Proactive Intelligence Engine (background scanner)
- Ledger agent (finance connectors not yet wired)
- Clerk agent (document OCR not yet built)

**Placeholder scan:** No TBDs. All code blocks complete. All file paths exact.

**Type consistency:**
- `AiBriefSection` exported from `MorningBriefReal.tsx` and imported in `today/page.tsx` ✅
- `QueueItem.contextCapsule` defined in `ApprovalQueue.tsx`, mapped in `ApprovalQueueServer.tsx` ✅
- `ChatRequest.user_id: Optional[str]` already in models.py — used by all agent `handle()` methods ✅
- `AuthorityResult` used consistently across engine.py, audit.py, __init__.py ✅
