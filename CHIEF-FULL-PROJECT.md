# CHIEF — Complete Project Document

> Single source of truth. Written 2026-05-28 from live codebase.
> Git repo: `MSherbinii/ChiefAI` — Supabase project `hjuanwztmwbwjzoquxtl`

---

## Table of Contents

1. [What Chief Is](#1-what-chief-is)
2. [The Problem We're Solving](#2-the-problem-were-solving)
3. [Product Vision](#3-product-vision)
4. [Target User](#4-target-user)
5. [Core Differentiators](#5-core-differentiators)
6. [Full Architecture](#6-full-architecture)
7. [The 7 Agents](#7-the-7-agents)
8. [The Intelligence Layer — How It Actually Works](#8-the-intelligence-layer--how-it-actually-works)
9. [Email Intelligence Engine v2 — Full Architecture](#9-email-intelligence-engine-v2--full-architecture)
10. [Life Graph Database Schema](#10-life-graph-database-schema)
11. [API Endpoints — All FastAPI Routes](#11-api-endpoints--all-fastapi-routes)
12. [Frontend Pages](#12-frontend-pages)
13. [Test Coverage](#13-test-coverage)
14. [What's Currently Working](#14-whats-currently-working)
15. [Roadmap](#15-roadmap)
16. [Jarvis Analysis — Competitor Study](#16-jarvis-analysis--competitor-study)
17. [Key Decisions Made](#17-key-decisions-made)
18. [Co-Founder Context](#18-co-founder-context)

---

## 1. What Chief Is

Chief is a **personal life operating system**. It is the intelligence layer that sits above all the tools a modern ambitious person uses — Gmail, GitHub, WHOOP, bank accounts, documents, calendar — and unifies them into a single context model.

The promise, in one sentence: **"Your life feels under management."**

Not more apps. Not another dashboard. Chief is the layer that notices things, connects dots across domains, and gives you leverage over your own situation. You don't come to Chief to do things — you come to Chief to understand what's happening and what matters most right now.

Chief runs as a monorepo:

```
chief/
├── apps/web/              # Next.js 15 App Router (TypeScript)
├── services/agents/       # Python FastAPI agent service (port 8001)
└── supabase/migrations/   # Postgres schema (auto-applied via GitHub → Supabase integration)
```

**Live stats (as of 2026-05-28):**
- Python files in agent service: **66**
- TypeScript/TSX files in web app: **70**
- Passing tests: **137 / 137** (0 failures)
- Git commits: **63**

---

## 2. The Problem We're Solving

### Context Fragmentation

An ambitious 24-year-old founder manages:
- 3–5 active projects across GitHub repos
- Gmail with 52,000+ emails containing live disputes, stalled applications, newsletters
- WHOOP recovery scores influencing whether to push or rest
- 2 bank accounts + subscriptions across 10+ services
- German bureaucracy (insurance, residency, university administration)
- Calendar with deadlines, commitments, and obligations

The problem is **not missing apps**. The problem is **scattered context**. Every decision requires manual aggregation across 8–12 tabs. The person who manages their context best wins. Chief is the context aggregator.

### The Specific Pain Points

1. **"What's happening with Deutsche Bank?"** — requires opening Gmail, searching, reading threads, building a mental model. Chief should just know.
2. **"Should I rest today or go hard at the gym?"** — requires cross-referencing WHOOP recovery with calendar pressure with recent project velocity. Chief should synthesize this.
3. **"Am I missing any critical emails?"** — 52,000 emails. The meaningful signal is buried. Chief builds a model of the email life (cases, entities, subscriptions) so the user doesn't have to.
4. **"What am I paying for?"** — requires checking multiple bank accounts, remembering subscription dates. Ledger handles this once the bank connectors are live.
5. **"Is this insurance document still valid?"** — documents scattered across downloads, email, and physical folders. Clerk OCRs and indexes everything.

---

## 3. Product Vision

Chief is the **CEO of your life**. CEOs don't do everything — they have a complete picture, they delegate, they know what's urgent vs important, and they make decisions with full context.

The key shift from all prior personal AI assistants: **proactive, not reactive**. Chief doesn't wait for you to ask. The agents run background scans every 4 hours. Chief notices:
- Your recovery has been declining for 3 days while your commit velocity has spiked — that's a burnout signal
- You have a stalled email thread with a debt collector that's 14 days without a reply
- You have 12 newsletter subscriptions you've never opened in 6 months
- You have a document expiring in 30 days

The morning brief at 7am UTC is generated before the user opens the app. When they log in, intelligence is already waiting.

**The long-term vision is a Life Graph** — a persistent knowledge graph of every entity (person, project, document, tool, place, concept) and relationship in the user's life. Every interaction, email, commit, purchase, and conversation enriches this graph. Over time, Chief develops a model of the user that no human assistant could replicate.

---

## 4. Target User

**Primary:** 22–35 year old founder, engineer, or ambitious student.

**Profile:**
- Multiple active side projects and/or a primary startup
- Tracks health metrics (WHOOP, Apple Watch, or manual)
- Multiple bank accounts, some subscriptions they've lost track of
- Sends many emails — work, admin, bureaucracy, networking
- Lives in Germany or German-speaking country (bureaucracy context)
- Uses AI tools daily but wastes time switching context between them
- Is "user zero" — willing to use an incomplete product because the vision is real

**Mohamed (actual user zero):**
- 52,459 emails in Gmail inbox
- Entities discovered: Twitch (106 interactions), ImmoScout24 (29), Revolut (14), BMW Group, Siemens
- Active cases: Deutsche Bahn booking/refund, job applications, apartment search
- 34 newsletter subscriptions detected (12 never opened)
- Based in Germany — German bureaucracy context throughout

**Secondary (Phase 5):** Co-founder workspaces — multiple users sharing a context layer for a shared venture.

---

## 5. Core Differentiators

### vs ChatGPT / Claude.ai (General Assistants)
- No persistent context model — every session starts fresh
- No health data integration
- No financial data
- No email intelligence (structure, cases, entities)
- No identity layer — doesn't know who you are
- No proactive scanning — purely reactive

### vs Apple Intelligence
- No Life Graph — just summaries of what's on-device
- No cross-domain reasoning (health + work + finance together)
- No long-horizon memory
- Apple doesn't know about your email cases, your project velocity, your insurance expiry
- No approval queue or action-taking capability

### vs Jarvis (Open Source Personal AI, RSALv2)
- RSALv2 license — code patterns studied and independently reimplemented, never copied
- Jarvis is single-user, SQLite, desktop/voice only — Chief is SaaS, multi-user, mobile-first web
- Jarvis has no health data integration — Chief has WHOOP connector
- Jarvis has no financial data — Chief has Ledger (Phase 3 real bank data via Tink/Plaid)
- Jarvis has no Email Intelligence Engine — Chief has 5-layer email model with case discovery
- Jarvis has no Momentum Score — Chief has cross-domain composite score with 7-day sparkline
- Chief's patterns inspired by: authority engine, agent hierarchy, knowledge graph schema, approval_patterns learning table — all reimplemented independently for Postgres/multi-user

### vs Superhuman / Email AI tools
- Email-only, no cross-domain context
- Chief understands the structure of your email life (cases, disputes, stalled applications), not just thread summaries

---

## 6. Full Architecture

### 6.1 Technical Stack

| Layer | Technology | Details |
|-------|-----------|---------|
| Frontend | Next.js 15 App Router | TypeScript, Tailwind CSS, Framer Motion |
| Backend | Python FastAPI | Port 8001, async, uvicorn |
| Database | Supabase Postgres | pgvector, RLS on all tables, project `hjuanwztmwbwjzoquxtl` |
| Auth | Supabase Auth | Email+password, Google OAuth, magic link fallback |
| Realtime | Supabase Realtime | Approval queue updates, brief generation progress |
| Storage | Supabase Storage | Document uploads (insurance cards, letters, IDs) |
| LLM — routing | Amazon Bedrock eu-central-1 | `eu.anthropic.claude-haiku-4-5-20251001-v1:0` |
| LLM — synthesis | Amazon Bedrock eu-central-1 | `eu.anthropic.claude-sonnet-4-6-20251231-v1:0` |
| LLM client | `anthropic.AnthropicBedrock()` | EU region endpoint, cheaper than direct Anthropic API |
| Embeddings | Amazon Titan Embeddings v2 | 1024 dims, padded to 1536 for pgvector compatibility |
| Structured agents | PydanticAI | `BedrockConverseModel` or `AnthropicModel` |
| Background jobs | APScheduler | `AsyncIOScheduler`, proactive scan 4h, daily brief 7am UTC |
| Connectors | Gmail, GitHub, WHOOP, Google Calendar, IMAP | OAuth tokens stored in `connector_tokens` |

### 6.2 Monorepo Structure

```
chief/
├── apps/web/
│   ├── app/
│   │   ├── (app)/                    # Authenticated app shell (sidebar layout)
│   │   │   ├── today/page.tsx        # Morning Brief + Momentum + Approval Queue
│   │   │   ├── chat/page.tsx         # Multi-agent chat
│   │   │   ├── domains/page.tsx      # Domain deep-dives
│   │   │   ├── graph/page.tsx        # Life Graph browser
│   │   │   ├── replay/page.tsx       # Weekly Replay
│   │   │   └── settings/page.tsx     # Profile + Connectors + Docs
│   │   ├── (auth)/                   # Unauthenticated routes
│   │   │   ├── login/page.tsx
│   │   │   └── auth/reset-password/
│   │   ├── onboarding/page.tsx       # 3-step wizard (outside app shell)
│   │   ├── api/                      # Next.js API routes
│   │   │   ├── auth/                 # Supabase auth handlers
│   │   │   ├── brief/generate/
│   │   │   ├── score/momentum/
│   │   │   ├── queue/                # Approval queue CRUD
│   │   │   ├── email/                # Email intelligence endpoints
│   │   │   └── connectors/           # OAuth redirect handlers
│   │   └── callback/                 # OAuth callback routing
│   └── components/
│       ├── today/                    # Brief sections, MomentumScore, ApprovalQueue
│       ├── chat/                     # ChatInterface, MessageBubble, SlashCommands
│       ├── domains/                  # Health/Work/Finance/Admin tab components
│       └── ui/                       # Shared design system components
│
├── services/agents/
│   ├── main.py                       # FastAPI app, all routes, APScheduler setup
│   ├── orchestrator.py               # Route messages to agents, quality scoring, memory
│   ├── guardrails.py                 # Input/output guardrails, response quality (0-100)
│   ├── memory.py                     # save_interaction, load_conversation_history
│   ├── feedback.py                   # RL feedback from approval/rejection, auto-approve
│   ├── proactive.py                  # Background scanner: health/comms/project anomalies
│   ├── hierarchy.py                  # Agent hierarchy, delegation, AGENT_HIERARCHY dict
│   ├── semantic_search.py            # pgvector semantic search over Life Graph
│   ├── embeddings.py                 # Titan/sentence-transformers embeddings
│   ├── voice_intent.py               # Classifies voice/text input → agent routing
│   ├── knowledge_extractor.py        # Extracts entities/relationships from emails+commits
│   ├── document_extractor.py         # Claude Vision OCR for uploaded documents
│   ├── pydantic_agents.py            # PydanticAI structured outputs factory
│   ├── llm.py                        # Bedrock/Anthropic client factory + model IDs
│   ├── models.py                     # ChatRequest, ChatResponse Pydantic models
│   ├── db.py                         # Supabase client helpers
│   ├── agents/
│   │   ├── pulse.py                  # Health agent
│   │   ├── echo.py                   # Communication agent (v2, case-aware)
│   │   ├── forge.py                  # Projects agent
│   │   ├── ledger.py                 # Finance agent
│   │   ├── clerk.py                  # Admin agent
│   │   └── scout.py                  # Research agent
│   ├── tools/
│   │   ├── health.py                 # fetch_health_context, log_workout
│   │   ├── comms.py                  # fetch_email_context, draft_email
│   │   ├── project.py                # fetch_project_context, fetch_velocity
│   │   ├── finance.py                # get_spending_report, detect_subscriptions
│   │   └── admin.py                  # fetch_documents, insurance_lookup
│   ├── connectors/
│   │   ├── gmail.py                  # Gmail OAuth sync → lg_communications + email_raw
│   │   ├── github.py                 # GitHub PAT sync → lg_projects, commit velocity
│   │   ├── whoop.py                  # WHOOP OAuth sync → lg_health
│   │   ├── google_calendar.py        # Calendar sync → commitments + facts
│   │   └── imap_email.py             # IMAP sync for university email
│   ├── email_intelligence/
│   │   ├── __init__.py               # Exports all pipeline functions
│   │   ├── deep_scanner.py           # Full Gmail inbox scan, email_raw storage
│   │   ├── entity_clusterer.py       # Group by domain, Haiku classification
│   │   ├── subscription_detector.py  # Pattern matching, engagement scoring
│   │   ├── case_discoverer.py        # Sonnet case discovery per entity
│   │   └── cross_entity_reasoner.py  # Link cases across entities, debt escalation
│   ├── scoring/
│   │   └── momentum.py               # calculate_momentum() → momentum_scores
│   ├── brief/
│   │   └── generator.py              # generate_morning_brief() → briefs table
│   ├── eval/
│   │   ├── runner.py                 # run_all_evaluations() — real Bedrock LLM eval
│   │   └── test_cases.py             # Curated test cases per agent
│   └── tests/
│       ├── conftest.py               # JWT mock, Supabase mock fixtures
│       ├── test_agent_integration.py # Guardrails, quality scoring, routing, voice intent, feedback
│       ├── test_api.py               # FastAPI endpoint tests
│       ├── test_authority.py         # Authority engine decisions per agent+tool
│       ├── test_case_discovery.py    # Cross-entity reasoner, Echo v2, case discoverer
│       ├── test_email_intelligence.py # Deep scanner, entity clusterer, subscription detector
│       ├── test_eval_framework.py    # Eval test case structure validation
│       ├── test_gmail_helpers.py     # Email parsing helpers
│       └── test_momentum.py          # Clamp and momentum calculation helpers
│
└── supabase/migrations/
    ├── 20260526000001_life_graph_schema.sql
    ├── 20260526000002_connector_tokens.sql
    ├── 20260526000003_authority_tables.sql
    ├── 20260526000004_briefs_checkins.sql
    ├── 20260526000005_entities_facts.sql
    ├── 20260526000006_briefs_add_best_move.sql
    ├── 20260526000007_staleness_trigger.sql
    ├── 20260526000008_agent_quality_log.sql
    ├── 20260526000009_vector_search_functions.sql
    ├── 20260526000010_jarvis_inspired_tables.sql
    ├── 20260526000011_documents_storage.sql
    └── 20260527000001_email_intelligence.sql
```

### 6.3 Key Design Principle: Intelligence Agnosticism

The intelligence layer (agents, LLM calls) is **fully decoupled** from the data layer (Life Graph tables). Any agent can be swapped, upgraded, or replaced without touching the schema. The Life Graph is the permanent asset; agents are the intelligence layer on top.

Consequences of this principle:
- Echo v1 → Echo v2 (case-aware) was a Python-only change — the DB schema stayed the same
- Switching from Haiku to Sonnet for Echo required one line change in `llm.py`
- The approval queue pattern means every consequential action is reversible — nothing is irreversible without user confirmation
- The RL feedback loop means the system improves without retraining models — it learns from user corrections stored in `approval_patterns` and `email_feedback`

### 6.4 Model Split Strategy

| Use case | Model | Reason |
|----------|-------|--------|
| Message routing (orchestrator) | Haiku | Fast, cheap — just classification |
| Entity classification (email) | Haiku | Pattern-heavy, doesn't need reasoning depth |
| Agent responses (most queries) | Haiku | Sufficient for tool-based factual answers |
| Echo agent specifically | Sonnet | Haiku over-refuses email access; Sonnet handles nuanced comms |
| Morning Brief generation | Sonnet | Cross-domain synthesis requires full reasoning |
| Case discovery | Sonnet | Complex multi-email situation analysis |
| Document OCR extraction | Sonnet (Vision) | Requires vision capability |
| Cross-entity reasoning | Sonnet | Linking cases across entities is the hardest reasoning task |

---

## 7. The 7 Agents

### 7.1 Chief (Orchestrator)

**Role:** Routes queries to sub-agents, synthesizes cross-domain responses.

**Authority level:** 10 (root of hierarchy — parent of all other agents)

**How it works:**
- Haiku classifies the incoming message to determine which agent(s) should handle it
- Cross-domain keywords (burnout, overall, big picture, week, everything) trigger multi-agent synthesis
- Sonnet is called for the synthesis step to combine outputs from multiple agents
- Delegates via `agent_messages` table when a task requires asynchronous processing

**Key files:** `orchestrator.py`, `hierarchy.py`

---

### 7.2 Pulse (Health Agent)

**Domain:** Body — recovery, sleep, workouts, nutrition, energy

**Authority level:** 7

**Key capabilities:**
- Reads `lg_health` (last 14 days) for WHOOP recovery, sleep scores, strain, workout history
- PydanticAI `HealthRecommendation` structured output for recommendation queries
- Proactive anomaly detection: recovery declining 3+ days = burnout signal alert
- Cross-domain awareness: can flag when health is affecting work velocity (via Chief synthesis)

**Connected data source:** WHOOP API via OAuth (connector_tokens.connector = 'whoop')

**Tool authority table:**

| Tool | Authority | Decision |
|------|-----------|----------|
| `log_workout` | allowed | Executes immediately |
| `generate_gym_plan` | approve_required | Goes to approval queue |
| `send_email` | denied | Outside domain |

---

### 7.3 Echo (Communication Agent — v2 Case-Aware)

**Domain:** Communications — Gmail threads, email cases, draft replies, staleness

**Authority level:** 6

**Why Echo uses Sonnet:** Haiku over-refuses email access when shown email content. Sonnet handles nuanced communication analysis without false refusals.

**Echo v2 Case-Aware Architecture:**

The old Echo (v1): fetch 50 newest threads → summarize → useless.

Echo v2 queries `email_cases` first:

```python
CASE_QUERY_KEYWORDS = [
    'fitstar', 'mcfit', 'deutsche bank', 'db', 'congstar',
    'stalled', 'dispute', 'debt', 'inkasso', 'pending', 'application',
    'immoscout', 'apartment', 'wohnung', 'job', 'application',
    'what happened', 'what\'s happening', 'status', 'update on'
]
```

**Processing flow:**
1. Detect if query is case-related (keyword match)
2. If yes → `_fetch_cases_context()` queries `email_cases` table ordered by priority
3. If no cases found → `_fetch_raw_email_context()` as fallback
4. Build timeline-aware response using case data
5. PydanticAI `CommunicationAnalysis` for stale-thread queries
6. Output guardrail: cannot claim an email was sent (must be queued through approval)

**Example interaction:**
```
User: "What's happening with Deutsche Bank?"

Echo v2 response:
"Case: Deutsche Bank Account Setup — STALLED (14 days)
Timeline:
• May 12 — Application submitted
• May 13 — Confirmation received (Ref: DB-2026-44521)
• May 15 — Identity verification completed
• Since then — No response

Suggested: Send follow-up referencing DB-2026-44521.
Draft ready — approve?"
```

---

### 7.4 Forge (Projects Agent)

**Domain:** Work — GitHub commit velocity, active projects, deadlines, calendar

**Authority level:** 7

**Key capabilities:**
- Reads `lg_projects` for active projects
- Reads commit velocity from `lg_health` (stored as metric='commit_velocity' from GitHub sync)
- Calendar events appear as upcoming deadlines via `commitments` table
- PydanticAI `ProjectStatus` for velocity queries
- Proactive velocity drop detection: 3+ days without commits on active project = alert

---

### 7.5 Ledger (Finance Agent)

**Domain:** Money — spending patterns, subscriptions, affordability checks

**Authority level:** 6

**Status:** Partially implemented. No bank connected yet (Phase 3 roadmap). Core tools exist but operate on manually-entered or mocked `lg_finance` data.

**Key tools:**
- `get_spending_report` — 30-day category breakdown from `lg_finance`
- `detect_subscriptions` — recurring payments identified by `is_subscription` flag
- `check_affordability` — compares a proposed cost against recent spending patterns

**Output guardrail:** Ledger cannot give unsolicited investment advice.

---

### 7.6 Clerk (Admin/Bureaucracy Agent)

**Domain:** Admin — German bureaucracy, documents, insurance, letters, deadlines

**Authority level:** 5

**Why Clerk exists:** German bureaucracy is uniquely complex — health insurance, residence registration (Anmeldung), university administration, tax filings, Krankenkasse, pension contributions. Non-native navigators lose hours to this. Clerk knows the system.

**Key capabilities:**
- Document library with insurance number lookup from `lg_documents`
- Claude Vision OCR for uploaded documents (insurance cards, letters, IDs, contracts)
- Draft reply workflow — always queued through approval_queue before sending
- Expiry tracking: documents with `expires_at` field, alerts when expiring soon
- German-specific sourcing for official deadlines and requirements

**Document extraction flow:**
1. User uploads document via `/settings`
2. Next.js API route calls `/documents/extract` on Python service
3. `document_extractor.py` sends image to Sonnet with structured extraction prompt
4. Returns: document type, key fields, extracted text, expiry date
5. Saved to `lg_documents` with `storage_path` pointing to Supabase Storage

---

### 7.7 Scout (Research Agent)

**Domain:** Research — market intelligence, comparisons, regulations, courses

**Authority level:** 5

**Key capabilities:**
- Market research and product comparisons
- German-specific sourcing (official government sources, legal deadlines)
- Course and certification recommendations
- Knowledge graph population: discovered entities and facts stored via `knowledge_extractor.py`
- Competitor analysis
- Regulation lookup (DSGVO, German insurance law, tenant rights)

---

## 8. The Intelligence Layer — How It Actually Works

### 8.1 Agent Processing Pipeline (per request)

Every message goes through this exact sequence:

```
1. Input guardrails (orchestrator.py → guardrails.py)
   └─ Injection pattern check: "ignore instructions", "pretend", "you are now"
   └─ Domain restriction: Pulse cannot answer finance questions
   └─ Sanitize: strip control characters, normalize whitespace

2. Memory context prepend (memory.py)
   └─ Load last N chat_messages for this user
   └─ Prepend as conversation history to LLM context

3. Agent fetch_context() (tools/)
   └─ Each agent fetches its domain's Life Graph data
   └─ Pulse: lg_health last 14 days
   └─ Echo: email_cases (case-aware) OR lg_communications
   └─ Forge: lg_projects + commitments + recent commits
   └─ Ledger: lg_finance transactions + subscriptions
   └─ Clerk: lg_documents + approval_queue pending

4. RAG context injection (semantic_search.py)
   └─ Query embedding via Titan Embeddings v2
   └─ pgvector cosine similarity search across entities + communications
   └─ Inject top-K relevant context chunks

5. Agent handle() — LLM call
   └─ Haiku for most agents
   └─ Sonnet for Echo, Morning Brief, Case Discovery

6. Output guardrails (guardrails.py)
   └─ Echo: cannot claim email was sent
   └─ Ledger: cannot give unsolicited investment advice
   └─ Minimum response length check (blocks 1-word answers)

7. Response quality scoring (guardrails.py)
   └─ 0-100 score based on: length, specificity, number presence, actionability
   └─ Agent-specific penalties (Pulse penalized if no recovery data when asked)

8. save_interaction() (memory.py)
   └─ Saves user message + assistant response to chat_messages
   └─ Metadata: agent name, timestamp, quality_score

9. save_quality_feedback() (feedback.py)
   └─ Deduped by message hash
   └─ Stores to agent_quality_log for performance monitoring
```

### 8.2 Authority Engine (Jarvis-inspired, independently reimplemented)

Every tool call passes through `check_authority(agent_name, tool_name)`.

The decision tree:

```
allowed         → execute immediately
notify          → execute + log to audit_trail
approve_required → create approval_queue item, return "[AWAITING_APPROVAL: ...]"
confirm_required → same as approve but marked urgent
denied          → blocked entirely, return error message
```

**Authority config per agent (from `hierarchy.py`):**

```python
AGENT_HIERARCHY = {
    'Chief': AgentNode(authority_level=10, tools_allowed=['*'], ...),
    'Pulse': AgentNode(
        authority_level=7,
        tools_allowed=['log_workout', 'fetch_health_context', ...],
        tools_requiring_approval=['generate_gym_plan', 'set_reminder'],
        tools_denied=['send_email', 'make_payment', ...]
    ),
    'Echo': AgentNode(
        authority_level=6,
        tools_requiring_confirmation=['send_email'],
        tools_requiring_approval=['draft_email', 'mark_read_all'],
        tools_denied=['make_payment', 'delete_email_permanent']
    ),
    'Ledger': AgentNode(
        authority_level=6,
        tools_requiring_confirmation=['cancel_subscription'],
        tools_denied=['make_payment_above_threshold']
    ),
    ...
}
```

**All decisions are logged to `audit_trail`** regardless of outcome. This is the non-negotiable principle. The audit trail is the foundation of trust.

**Auto-approve learning:**
- `approval_patterns` table tracks consecutive approvals per (user, agent, tool)
- After 5 consecutive approvals of the same pattern → `auto_approve = true`
- Future identical requests skip the queue and execute with auto-approve badge
- Reversible: user can revoke auto-approve from /settings

### 8.3 Proactive Intelligence Engine

`proactive.py` runs via APScheduler:

```python
# Every 4 hours for all users
scheduler.add_job(run_proactive_scan_all_users, 'interval', hours=4)

# Daily brief at 7am UTC
scheduler.add_job(run_daily_brief_for_all, 'cron', hour=7, minute=0)
```

**Proactive scanners:**

| Scanner | Signal | Alert type |
|---------|--------|------------|
| Health anomaly | Recovery < 50% for 3+ consecutive days | `recovery_declining` |
| Cross-domain burnout | Low recovery + high commit velocity | `burnout_risk` |
| Stale communication | Thread with no reply > 7 days, user sent last | `stale_thread` |
| Velocity drop | No commits on active project for 3+ days | `velocity_drop` |
| Deadline approaching | Commitment `when_due` within 48 hours | `deadline_near` |
| Document expiry | `lg_documents.expires_at` within 30 days | `document_expiring` |

**Deduplication:** One alert per `alert_type` per user per day. Alerts stored in `approval_queue` with `action_type = 'proactive_alert'`.

### 8.4 PydanticAI Structured Outputs

For queries requiring structured data (not conversational responses):

```python
# pydantic_agents.py

class HealthRecommendation(BaseModel):
    summary: str
    recovery_trend: str          # improving / stable / declining
    recommended_action: str      # rest / train / light_session
    reasoning: str
    confidence: float

class CommunicationAnalysis(BaseModel):
    stale_threads: list[str]
    urgent_threads: list[str]
    draft_suggestions: list[str]
    cases_detected: list[str]

class ProjectStatus(BaseModel):
    active_projects: list[str]
    velocity_trend: str
    blockers: list[str]
    next_milestone: str
```

**Three-tier fallback:**
1. PydanticAI with `BedrockConverseModel` → structured output
2. Raw LLM call + JSON parse → best effort
3. Field defaults → graceful degradation (never crashes)

### 8.5 Morning Brief Generation

The morning brief is the daily synthesis. Generated by Sonnet with full Life Graph context.

**Brief structure:**
```json
{
  "greeting": "Good morning, Mohamed",
  "sections": [
    {
      "domain": "body",
      "title": "Body",
      "content": "Recovery at 72%. Sleep was 7h 20m. Trend stable.",
      "alerts": []
    },
    {
      "domain": "work",
      "title": "Work",
      "content": "3 active projects. Chief has 12 commits this week...",
      "alerts": ["Lumina velocity dropped — 0 commits in 2 days"]
    },
    {
      "domain": "admin",
      "title": "Admin",
      "content": "2 items in approval queue. 1 document expiring in 28 days.",
      "alerts": []
    }
  ],
  "life_debt": {
    "items": ["Follow up on Deutsche Bank account", "Schedule WHOOP sync"],
    "score": 73
  },
  "best_move": "Address the Deutsche Bank stall — draft a follow-up via Echo",
  "patterns": ["Work output is high. Recovery needs attention.",
                "Admin backlog has been growing this week."]
}
```

**Brief auto-generation:** On first `/today` visit, if no brief for today exists, `BriefLoader` triggers `/api/brief/generate` with a 45-second animated loading state using Sonnet. Subsequent visits read from the `briefs` table.

### 8.6 Momentum Score

The Momentum Score is a **cross-domain composite (0–100)** that represents how "under control" life feels right now.

**Domain weights and inputs:**

| Domain | Weight | Source |
|--------|--------|--------|
| Body | 25% | WHOOP recovery score, sleep, workout consistency |
| Work | 25% | Commit velocity, project status, deadline pressure |
| Money | 20% | Spending vs budget, subscription health, debt signals |
| Admin | 15% | Approval queue backlog, document expiries, cases pending |
| Discipline | 15% | Goal progress, streak consistency, commitment completion rate |

**Score history:** Stored in `momentum_scores` table — one row per calculation. The `/today` page shows a 7-day sparkline with delta vs yesterday.

**Auto-calculation:** `calculate_momentum()` runs before every morning brief generation. Also callable via `/score/momentum` API endpoint.

---

## 9. Email Intelligence Engine v2 — Full Architecture

### 9.1 Why We Rebuilt This

The original email connector (v1) was naive: sync 50 newest Gmail threads → store in `lg_communications` → Echo reads them. This is the same as opening Gmail. It provides no intelligence.

The user has **52,459 emails**. The intelligence is not in the newest 50. The intelligence is in the **structure** — the ongoing situations, the entity relationships, the subscription noise — that emerges from analyzing the full inbox.

Email Intelligence v2 treats the inbox as a structured dataset, not a message stream.

### 9.2 The 5-Layer Model

```
Layer 1: email_raw           — every email, complete inbox scan
Layer 2: entities (upgraded) — classified senders with relationship_type
Layer 3: email_cases         — ongoing situations (disputes, applications, stalled accounts)
Layer 4: email_subscriptions — recurring noise, engagement-scored
Layer 5: email_feedback      — RL training signal from user corrections
```

### 9.3 Implementation Modules

**`email_intelligence/deep_scanner.py`** — Full Gmail inbox pagination
- Fetches ALL message IDs (lightweight list call)
- Batch-fetches full metadata in pages of 500
- Scans INBOX + SENT + STARRED labels separately
- Stores every email to `email_raw` (unique on gmail_id)
- Updates `email_scan_status` with progress for frontend polling
- Mohamed's result: **52,459 emails stored**

**`email_intelligence/entity_clusterer.py`** — Group by domain, classify
- Groups emails by sender domain (noreply@db.de + service@db.de → Deutsche Bank)
- Exception: personal email domains (gmail.com, yahoo.de, gmx.de, t-online.de) are not clustered
- Haiku classifies `relationship_type` for each entity: `service_provider`, `bank`, `debt_collector`, `employer`, `professor`, `newsletter`, `marketplace`, `government`, `friend`, `unknown`
- Updates existing `entities` table rows with email-specific fields: `email_domains`, `first_contact`, `last_contact`, `interaction_count`, `engagement_score`
- Mohamed's result: **339 entities classified**. Notable: Twitch (106 interactions), ImmoScout24 (29), Revolut (14), BMW Group, Siemens

**`email_intelligence/subscription_detector.py`** — Pattern-based, no LLM needed
- Detection criteria: sender emails 3+ times, regular interval (±30% variance), contains unsubscribe link
- Engagement scoring: `engagement_score = (replied_count * 3 + opened_count) / total_received`
- Staleness penalty: `>365 days since last email → 0.0`, `>90 days → 0.2`
- Detects unsubscribe links from headers + body text (including German: "abmelden")
- Mohamed's result: **34 subscriptions detected**
  - Dead (score < 0.1): RoboForex, BestBuy, Lenovo, WarriorPlus (2019–2021)
  - Active: LinkedIn Jobs, ImmoScout24 alerts, various German services

**`email_intelligence/case_discoverer.py`** — Sonnet case discovery per entity
- For each entity with `sent_count > 0` (user had actual correspondence)
- Fetches all threads (sent + received) for that entity
- Feeds to Sonnet with structured prompt: "Identify distinct Cases (ongoing situations)"
- Case signals: money references, deadlines, reference numbers, account numbers, escalation patterns, temporal clustering (burst then silence = stalled)
- Each case: title, status, priority, category, summary, pending_action, timeline (JSON array)
- Upserts to `email_cases` table
- Case statuses: `open`, `progressing`, `stalled`, `needs_action`, `resolved`
- Case priorities: `low`, `normal`, `high`, `critical`

**`email_intelligence/cross_entity_reasoner.py`** — Link cases across entities
- Detects debt escalation pattern: Company A emails stop + Collection agency B emails start = same case
- Matches reference numbers across entities: same `DB-2026-44521` in two entities = linked
- Auto-merges linked cases into a master case with combined timeline
- Mohamed's real cases discovered: Deutsche Bahn booking/refund dispute, job applications cluster, apartment search via ImmoScout24

### 9.4 Case Discovery Quality (Mohamed's Results)

From the initial scan on Mohamed's real inbox:

| Case | Category | Priority | Status | Pending Action |
|------|----------|----------|--------|---------------|
| Deutsche Bank Account Setup | account_setup | high | stalled | Send follow-up, Ref: DB-2026-44521 |
| Deutsche Bahn Booking/Refund | dispute | high | needs_action | File refund claim |
| Fitstar/McFit Debt Dispute | dispute | critical | needs_action | Respond to debt collector |
| Job Applications 2026 | application | normal | progressing | Follow up on 3 pending |
| Apartment Search ImmoScout24 | service_request | normal | open | Respond to 2 landlords |

### 9.5 RL Feedback Loop

User corrections are stored as training signals in `email_feedback`:

| Signal | feedback_type | Effect |
|--------|---------------|--------|
| "Yes, correct" | `case_confirm` | +1.0 weight on this case type |
| "No, wrong" | `case_reject` | Sets case `status='resolved'`, `confidence=0.1` |
| "These are the same" | `case_merge` | Triggers `merge_linked_cases()` |
| "This is a bank, not unknown" | `entity_correct` | Immediately updates `entities.relationship_type` |
| User explains situation verbally | `context_injection` | Stored as `email_cases.user_notes` |
| User asks about a case | implicit | +0.2 priority boost in next scan |

**Learning outcomes over time:**
1. Entity classification improves: after confirming "Inkasso X is a debt collector", Haiku zero-shots similar patterns
2. Case priority calibration: learning that financial disputes are always `high` for this user
3. Action templates: after 3 approved follow-up drafts, Echo pre-drafts the 4th
4. Subscription preferences: keeps tech newsletters, removes marketing → future detection calibrated

### 9.6 Initial Interview Flow

After case discovery runs, `GET /email/present-cases/{user_id}` returns a structured message:

```
I've analyzed your full inbox. Here's what I found:

1. 🔴 Fitstar/McFit Debt Dispute (Needs Action)
   Debt collector escalation from gym membership dispute.
   → Next: Respond to Inkasso letter within 14 days

2. 🟠 Deutsche Bank Account Setup (Stalled)
   Applied May 12, identity verified May 15. No response since.
   → Next: Send follow-up referencing DB-2026-44521

3. 🟡 Deutsche Bahn Refund (Open)
   Ticket booking dispute from April travel.
   → Next: File refund claim via DB portal

Also found 12 newsletters you never open — want me to clean those up?

Did I get these right? Anything missing or wrong?
```

User response → stored as RL feedback → improves future discovery accuracy.

---

## 10. Life Graph Database Schema

All tables are in the `public` schema with Row Level Security enabled. Every table has a `user_id FK → profiles(id)` for multi-tenancy.

### Core Life Graph Tables

| Table | Purpose | Key fields |
|-------|---------|-----------|
| `profiles` | Extends `auth.users` | `display_name`, `timezone` |
| `lg_people` | Known people in the user's life | `name`, `relationship`, `importance (1-5)`, `last_interaction`, `embedding (vector(1536))` |
| `lg_projects` | Active and past projects | `name`, `type`, `status`, `deadline`, `tools[]` |
| `lg_health` | Health metrics timeseries | `metric` (recovery/sleep/strain/workout), `value (jsonb)`, `source` (whoop/manual), `recorded_at` |
| `lg_finance` | Financial transactions | `account`, `type`, `amount_cents`, `currency`, `category`, `is_subscription`, `recurring_period` |
| `lg_communications` | Email/message threads | `thread_id`, `channel`, `participants[]`, `subject`, `summary`, `staleness_days`, `urgency`, `related_person_id`, `related_project_id` |
| `lg_documents` | Documents and files | `type` (insurance/contract/letter/id), `title`, `extracted_fields (jsonb)`, `storage_path`, `expires_at` |
| `lg_goals` | User goals per domain | `domain` (health/work/money/admin), `title`, `target`, `progress (0-100)`, `deadline`, `blockers[]` |

### Intelligence Tables

| Table | Purpose | Key fields |
|-------|---------|-----------|
| `entities` | Knowledge graph nodes | `type` (person/project/tool/concept/place/event/document), `name`, `properties (jsonb)`, `source`, `embedding`, `relationship_type`, `email_domains[]`, `interaction_count`, `engagement_score` |
| `facts` | Subject → predicate → object | `subject_id`, `predicate`, `object`, `object_id`, `confidence (0.0-1.0)`, `source` |
| `relationships` | Entity-to-entity links | `from_id`, `to_id`, `type`, `properties (jsonb)` |
| `briefs` | Morning Brief storage | `brief_date`, `type` (morning), `greeting`, `sections (jsonb)`, `life_debt (jsonb)` |
| `goal_check_ins` | Replay history | `type`, `brief_id`, `highlights[]`, `lowlights[]`, `patterns_noticed[]`, `narrative` |
| `momentum_scores` | Score snapshots | `total (0-100)`, `body`, `money`, `work`, `admin`, `discipline` — all `(0-100)` |
| `chat_messages` | Conversation history | `role` (user/assistant), `content`, `agent`, `metadata (jsonb)` |
| `agent_quality_log` | Response quality tracking | `agent`, `message_hash`, `quality_score (0-100)`, `issues[]` |

### Action & Authority Tables

| Table | Purpose | Key fields |
|-------|---------|-----------|
| `approval_queue` | Pending actions awaiting user approval | `agent`, `action_type`, `risk_level`, `title`, `description`, `payload (jsonb)`, `context_capsule (jsonb)`, `status` (pending/approved/rejected), `expires_at` |
| `audit_trail` | Every tool call logged regardless of outcome | `agent`, `tool_name`, `action_category`, `authority_decision`, `executed`, `execution_time_ms`, `input_data`, `output_data` |
| `approval_patterns` | Auto-approve learning | `agent`, `action_category`, `tool_name`, `consecutive_approvals`, `auto_approve (bool)` |

### Workflow Tables

| Table | Purpose | Key fields |
|-------|---------|-----------|
| `commitments` | Task lifecycle (pending→active→completed) | `agent`, `what`, `why`, `when_due`, `priority`, `status`, `retry_count`, `assigned_to`, `created_from`, `result` |
| `agent_messages` | Inter-agent communication | `from_agent`, `to_agent`, `type` (task/report/question/escalation), `content`, `priority`, `requires_response`, `responded`, `commitment_id` |
| `recent_objects` | Bounded LRU access log (max 50 per user) | `object_type`, `object_id`, `label`, `accessed_at` — capped by DB trigger |
| `connector_tokens` | OAuth tokens per connector | `connector`, `access_token`, `refresh_token`, `token_expiry`, `extra (jsonb)`, `last_synced_at`, `sync_status` |

### Email Intelligence Tables (migration 20260527000001)

| Table | Purpose | Key fields |
|-------|---------|-----------|
| `email_raw` | Complete inbox store (52,459 rows for Mohamed) | `gmail_id`, `thread_id`, `from_email`, `subject`, `snippet`, `body_text`, `date`, `labels[]`, `is_sent`, `embedding`, `processed` |
| `email_cases` | Ongoing situations | `title`, `status` (open/progressing/stalled/needs_action/resolved), `priority` (low/normal/high/critical), `category`, `summary`, `entities[]`, `email_ids[]`, `pending_action`, `stalled_since`, `user_notes`, `timeline (jsonb)`, `confidence` |
| `email_subscriptions` | Detected newsletters | `sender_email`, `frequency`, `avg_interval_days`, `total_received`, `engagement_score`, `has_unsubscribe_link`, `unsubscribe_url`, `status`, `user_decision` |
| `email_feedback` | RL training signals | `feedback_type` (case_confirm/case_reject/case_merge/entity_correct/priority_change/action_approve/action_reject), `target_id`, `target_type`, `old_value`, `new_value`, `context` |
| `email_scan_status` | Scan progress tracking | `status` (idle/scanning/clustering/detecting_subscriptions/complete/error), `total_emails`, `scanned_emails`, `error_message`, `started_at`, `completed_at` |

---

## 11. API Endpoints — All FastAPI Routes

Base URL: `http://localhost:8001`

### Core

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check — returns `{status: "ok", service: "chief-agents"}` |
| POST | `/chat` | Main chat endpoint — routes to orchestrator, returns ChatResponse |
| POST | `/voice/classify` | Classify voice transcript → agent routing decision (VoiceIntent) |

### Sync Connectors

| Method | Path | Description |
|--------|------|-------------|
| POST | `/sync/google` | Trigger async Gmail sync (OAuth tokens from connector_tokens) |
| POST | `/sync/github` | Trigger async GitHub sync (commit history, repos) |
| POST | `/sync/whoop` | Trigger async WHOOP sync (recovery, sleep, workouts) |
| POST | `/sync/imap_uni` | Trigger async IMAP sync (university email) |
| POST | `/sync/google_calendar` | Trigger async Google Calendar sync → commitments + facts |
| POST | `/connectors/imap/verify` | Verify IMAP credentials before storing (test connection) |

### Email Intelligence

| Method | Path | Description |
|--------|------|-------------|
| POST | `/email/deep-scan` | Trigger full inbox pipeline: deep scan → cluster → detect subscriptions |
| GET | `/email/scan-status/{user_id}` | Poll current deep scan progress |
| GET | `/email/subscriptions/{user_id}` | List detected email subscriptions (ordered by engagement ASC) |
| GET | `/email/stats/{user_id}` | Email intelligence summary: total emails, subscriptions, entities |
| POST | `/email/cases/run-discovery` | Trigger case discovery → cross-entity reasoning pipeline |
| GET | `/email/cases/{user_id}` | List active email cases (excludes resolved, ordered by priority) |
| GET | `/email/case/{case_id}` | Full case details with timeline |
| POST | `/email/case/{case_id}/note` | Add user context/note to a case (stores as RL signal) |
| POST | `/email/feedback` | Store RL feedback: case_confirm/reject/merge, entity_correct |
| POST | `/email/cases/merge` | Merge two cases user identifies as the same situation |
| POST | `/email/unsubscribe` | Queue unsubscribe action for a subscription via approval_queue |
| GET | `/email/present-cases/{user_id}` | Get structured cases summary for Initial Interview (Echo presents to user) |

### Intelligence Generation

| Method | Path | Description |
|--------|------|-------------|
| POST | `/score/momentum` | Calculate and store Momentum Score for user |
| POST | `/brief/generate` | Generate Morning Brief via Sonnet, stores to briefs table |
| POST | `/proactive/scan` | Run proactive scan for a single user |
| POST | `/knowledge/extract` | Trigger background knowledge graph extraction (emails + commits) |
| POST | `/embeddings/update` | Update entity + communication embeddings via Titan |

### Feedback & Performance

| Method | Path | Description |
|--------|------|-------------|
| POST | `/feedback/approval` | Record approval/rejection outcome, update approval_patterns |
| GET | `/feedback/performance/{user_id}/{agent}` | Agent performance report (approval rate, quality scores) |

### Documents

| Method | Path | Description |
|--------|------|-------------|
| POST | `/documents/extract` | Claude Vision OCR extraction from uploaded document image |

### Hierarchy

| Method | Path | Description |
|--------|------|-------------|
| GET | `/hierarchy` | Full agent hierarchy tree (all 7 agents, authority levels, tools) |
| GET | `/hierarchy/tasks/{user_id}/{agent}` | Pending tasks for an agent from agent_messages |
| POST | `/hierarchy/delegate` | Delegate a task from one agent to another |

### Evaluation

| Method | Path | Description |
|--------|------|-------------|
| POST | `/eval/run` | Run full agent evaluation suite — makes real Bedrock calls, returns quality report |

---

## 12. Frontend Pages

### `/login`

Premium split-panel layout matching the Lumina V2 design system.

**Left panel:** Brand panel — Chief logo, tagline, abstract design elements

**Right panel:** Auth card
- Email + password fields with validation
- "Sign in with Google" button (Google OAuth via Supabase)
- "Sign in with GitHub" button (GitHub OAuth via Supabase)
- "Forgot password?" link → `/auth/reset-password` page
- Toggle between Sign In and Sign Up

**Auth flow:**
1. Supabase `signInWithPassword()` or `signInWithOAuth()`
2. Callback at `/callback` → checks if `profiles` row exists
3. No profile → redirect to `/onboarding`
4. Profile exists → redirect to `/today`

---

### `/onboarding` (3-step wizard, outside app shell)

**Step 1: Identity**
- Name input
- Timezone auto-detected from browser, dropdown to override
- Writes to `profiles.display_name` and `profiles.timezone`

**Step 2: Role Selection**
- 6 role cards: Founder / Student / Freelancer / Engineer / Creator / Other
- Single select, required
- Role written to `profiles` extra fields

**Step 3: Focus Goals**
- Chip input with role-based suggestions
- Max 3 focus tags
- Examples: "ship weekly", "sleep 8h", "clear inbox", "code every day"
- Writes to `lg_goals` table as initial goals

On completion → redirect to `/today`.

---

### `/today` (Main Dashboard)

The primary screen. Everything important at a glance.

**BriefLoader:**
- On first visit with no brief for today: triggers `/api/brief/generate`
- 45-second animated loading state with Sonnet generation progress
- Displays generated brief sections once complete
- RegenerateButton: force-regenerate brief with fresh Life Graph data

**MomentumScore:**
- Large circular ring displaying the composite score (0–100)
- 5 domain bars: Body / Work / Money / Admin / Discipline
- 7-day sparkline showing score history
- Delta vs yesterday (e.g., "+4 vs yesterday")

**LifeDebt Panel:**
- Outstanding admin items that keep appearing in briefs
- Persistent tasks that haven't been resolved

**Morning Brief Sections:**
- Body section: recovery, sleep, workout
- Work section: project velocity, commit streak, stale threads
- Admin section: approval queue count, expiring documents

**Best Move + Patterns:**
- Sonnet's single recommended action for today
- Recurring patterns noticed across the week

**ApprovalQueue:**
- Expandable context capsules for each pending action
- Context capsule shows: sources used, reasoning, confidence level
- Auto-approve badge for items that have passed the learning threshold
- Approve / Reject buttons with optimistic UI

---

### `/chat` (Multi-Agent Chat)

**Agent color badges:**
| Agent | Color |
|-------|-------|
| Chief | Indigo |
| Pulse | Teal |
| Echo | Violet |
| Forge | Green |
| Ledger | Amber |
| Clerk | Blue |
| Scout | Orange |

**Slash commands:**
- `/brief` — generate morning brief
- `/score` — show Momentum Score breakdown
- `/scan` — run proactive scan and surface alerts

**Features:**
- Voice input button (microphone icon — routes to `/voice/classify` stub, Phase 1B)
- Framer Motion message transitions (slide in, agent badge fade)
- Persistent conversation history from `chat_messages` table
- Agent attribution on every response — user always knows which agent answered

---

### `/domains` (Domain Deep-Dives)

Tabbed interface for detailed domain analysis.

**Health tab:**
- Recovery % (latest WHOOP reading)
- Average sleep (7-day)
- Workouts count (this week)
- 7-day recovery bar chart
- Source: `lg_health` metrics

**Work tab:**
- Total commits (this week)
- Repos active (with commits in last 7 days)
- Stale threads count (comms with no reply > 7 days)
- Projects list with status badges
- Stale communications list with "Draft reply" CTA

**Finance tab:**
- 30-day spend total
- Subscription total (monthly recurring from `lg_finance.is_subscription = true`)
- Subscription line items with amounts

**Admin tab:**
- Documents count
- Documents expiring soon (within 30 days)
- Approval queue items count
- Links to `/settings` for document management

---

### `/graph` (Life Graph Browser)

Visual explorer for the knowledge graph.

**Stats row:**
- Total entities count
- Total relationships count
- Total facts count

**Type filter pills:**
- person / project / tool / place / concept / event / document

**Search input:**
- Queries `entities` by name (Postgres text search)

**Entity grid:**
- Name, type badge, properties preview, source tag
- Clicking an entity → shows its facts list and relationships

**Recent facts list:**
- Subject → predicate → object → confidence%
- Sorted by `created_at DESC`

---

### `/replay` (Weekly Replay)

Narrative view of historical check-ins from `goal_check_ins` table.

**Weekly narrative card:**
- Week date range
- Momentum start → end (with trend arrow TrendingUp/TrendingDown)
- Highlights (things that went well)
- Lowlights (things that slipped)
- Patterns noticed by Chief AI

---

### `/settings` (Settings)

**Profile section:**
- Name, email, timezone, avatar (upload to Supabase Storage)
- Editable inline

**Connectors:**

| Connector | Status | Controls |
|-----------|--------|---------|
| Gmail | Connected ✓ (shows last synced time) | Sync button → POST `/sync/google` |
| Google Calendar | Connected/Not connected | Connect → OAuth flow |
| GitHub | Connected/Not connected | Connect → OAuth flow or PAT input |
| WHOOP | Connected/Not connected | Connect → WHOOP OAuth flow |
| IMAP (uni email) | Not connected | IMAP host/email/password form → `/connectors/imap/verify` |

Each connector shows: status dot (green/red/grey), last sync timestamp, sync button.

**Document upload:**
- Drag-and-drop or file picker
- Doc type selector: insurance_card / letter / id / contract / certificate / other
- On upload → Next.js API route → Python `/documents/extract` (Claude Vision OCR)
- Extracted fields shown in confirmation modal
- Document saved to `lg_documents` + Supabase Storage

**Agent Status panel:**
- All 7 agents listed with descriptions
- Status dots (green = active, based on whether agent service is reachable)
- Last interaction timestamp per agent

---

## 13. Test Coverage

**Total: 137 tests, 0 failures, 4.51 seconds**

### Test Files

**`tests/test_agent_integration.py`** — Core agent system tests
- `TestInputGuardrails` (10 tests): allows valid queries, blocks prompt injections ("ignore instructions", "pretend you are", "you are now"), blocks cross-domain violations (Pulse asked finance questions, Echo asked health questions), sanitizes valid input
- `TestOutputGuardrails` (8 tests): blocks Echo claiming email was sent, blocks very short responses (<20 chars), blocks unsolicited investment advice from Ledger, allows normal responses
- `TestResponseQuality` (7 tests): high-quality responses score >70, generic responses score <50, responses with specific numbers score higher, verbose responses penalized, quality result has all required keys, score clamped 0-100, Pulse penalized for missing recovery data
- `TestOrchestratorRouting` (4 tests): routing prompt mentions all agents, describes Pulse and Echo domains correctly
- `TestVoiceIntent` (9 tests): domain→agent mapping complete, workout logs route to Pulse, email drafts route to Echo, fallback on LLM error, fallback on bad JSON, low confidence routes to Chief, high confidence routes to specific agent, empty/whitespace transcripts return fallback
- `TestFeedbackLoop` (7 tests): module imports, ApprovalOutcome model valid, rejection handling, auto-approve returns false for unknown, auto-approve returns true when pattern set, graceful exception handling, performance report model
- `TestProactiveEngine` (8 tests): module imports, alert model valid, default risk level, no alerts for empty data, no alerts for insufficient data, declining recovery generates alert, no comms alerts for empty data, stale thread generates Echo alert
- `TestPulseAgentUnit`, `TestEchoAgentUnit`, `TestForgeAgentUnit` (3 tests): agents return ChatResponse, handle missing user_id
- `TestHierarchy` (3 tests): hierarchy has all 7 agents, Chief is root, authority inheritance
- `TestVoiceIntentExtended` (3 tests): finance routes to Ledger, admin routes to Clerk, general routes to Chief
- `TestAllAgentsInstantiate` (6 tests): all 6 sub-agents instantiate without errors

**`tests/test_api.py`** — FastAPI endpoint tests
- Health endpoint returns 200
- Chat endpoint routes to agent correctly
- Sync Google returns sync_started
- Momentum endpoint calls calculator
- Brief generate endpoint calls generator

**`tests/test_authority.py`** — Authority engine
- Pulse: log_workout allowed, generate_gym_plan requires approval, send_email denied
- Echo: send_email requires confirmation, draft_email requires approval
- Ledger: cancel_subscription requires confirmation
- Unknown agent defaults to approval_required
- Unknown tool defaults to approval_required

**`tests/test_case_discovery.py`** — Email cases and Echo v2
- `TestCrossEntityReasonerHelpers`: extracts German-format reference numbers, order IDs, empty text; detects debt signals (Inkasso, Mahnung, normal email, subscription email)
- `TestEchoV2Context`: Echo imports correctly, case query keyword detection works, agent instantiates, builds interview message with cases, builds interview message when empty
- `TestCaseDiscovererHelpers`: case status valid values, priority ordering correct, case discovery prompt has correct sections, cross-entity system has German debt patterns (Inkasso, Mahnung, Schuldner)

**`tests/test_email_intelligence.py`** — Email pipeline unit tests
- `TestDeepScannerHelpers` (4 tests): parse message basic, parse sent message, parse bare email address, parse thread ID
- `TestEntityClustererHelpers` (5 tests): extract domain from standard email, German bank email, property site; detect personal emails (gmail, yahoo.de, t-online.de); confirm bank and fitstar not personal
- `TestSubscriptionDetectorHelpers` (8 tests): unsubscribe link in snippet, German "abmelden" link, no link in normal email; newsletter subject patterns (Newsletter, Digest); normal subject not detected; Mahnung (debt notice) not newsletter; noreply@ triggers detection

**`tests/test_eval_framework.py`** — Eval test case structure
- All test cases have required fields, correct agent routing, no forbidden patterns, unique names, minimum coverage, all in ALL_CASES list, must_contain terms are lowercase

**`tests/test_gmail_helpers.py`** — Email parsing
- Extract email + name from display name format, bare email, quoted name, dotted username

**`tests/test_momentum.py`** — Score calculation
- Clamp function: normal range, below min, above max

### Eval Suite (separate from unit tests)

`eval/runner.py` — runs real Bedrock LLM calls against curated test cases.

**Last reported results (commit `14229e0`):**
- 90% pass rate
- 97.5/100 average quality score
- Test cases cover: Pulse health queries, Echo stale thread detection, Forge velocity analysis, Ledger subscription queries, Clerk document lookup, Scout research queries

---

## 14. What's Currently Working

As of **2026-05-28** (git log + test results):

### Fully Working (green in production)

**Agent service:**
- All 7 agents instantiate and respond to queries
- Orchestrator routes correctly with Haiku classification
- Input + output guardrails pass 137/137 tests
- Authority engine: allowed/notify/approve_required/confirm_required/denied
- Approval queue with context capsules
- Auto-approve learning (5 consecutive approvals → auto_approve = true)
- Audit trail logging every tool call
- Proactive scanner: health anomalies, stale comms, velocity drops, burnout signals
- APScheduler: 4h proactive scan + 7am brief
- Morning Brief generation with Sonnet (full Life Graph context)
- Momentum Score calculation (5-domain composite)
- Voice intent classifier (LLM-based, with fallback)
- PydanticAI structured outputs (HealthRecommendation, CommunicationAnalysis, ProjectStatus)
- Document OCR extraction via Claude Vision
- Knowledge graph extraction from emails + commits
- pgvector semantic search with Titan embeddings
- Agent hierarchy + delegation + commitments
- Agent quality logging + performance metrics

**Email Intelligence Engine (fully built, tested, pending live validation):**
- Deep scanner: full Gmail pagination, 52,459 emails stored for Mohamed
- Entity clusterer: 339 entities classified with relationship_type
- Subscription detector: 34 subscriptions found, engagement-scored
- Case discoverer: Sonnet-based situation identification per entity
- Cross-entity reasoner: debt escalation detection, reference number matching
- Echo v2: case-aware responses, CASE_QUERY_KEYWORDS detection
- All email API endpoints: deep-scan, scan-status, cases, case, feedback, merge, unsubscribe, present-cases

**Frontend:**
- Login: split panel, email/password, Google OAuth, GitHub OAuth, forgot password
- Onboarding: 3-step wizard, role selection, focus tags, writes profiles + lg_goals
- Today: BriefLoader (45s animation), MomentumScore (ring + bars + sparkline + delta), LifeDebt, Brief sections, ApprovalQueue with context capsules
- Chat: agent color badges, slash commands (/brief /score /scan), Framer Motion transitions
- Domains: Health/Work/Finance/Admin tabs with real Life Graph data
- Graph: entity grid, type filters, search, fact viewer
- Replay: weekly narratives from goal_check_ins
- Settings: profile edit, connector cards with sync buttons, document upload + OCR, agent status

### Connected but Awaiting Real Data

| Connector | Status |
|-----------|--------|
| Gmail | OAuth connected, sync working, deep scan run on Mohamed's inbox |
| Google Calendar | Connector built, OAuth flow ready |
| GitHub | Connector built, PAT setup needed |
| WHOOP | OAuth flow built, awaiting WHOOP credentials |
| IMAP (uni) | Connector built, IMAP verify endpoint working |
| Banks / Finance | Phase 3 — Tink/Plaid not yet integrated |

### Known Gaps (not yet built)

- Subscription cleanup UI in frontend (API exists, UI not built)
- Case management UI in frontend (API exists, UI not built)
- Case-aware context in `/today/page.tsx` (not yet surfaced on Today page)
- Mobile app (Phase 4)
- Bank connectors (Phase 3)
- Voice TTS (Phase 1B — ElevenLabs not yet integrated)

---

## 15. Roadmap

### Phase 1B: Voice (Next, ~2 weeks)

**Goal:** Capture and process voice commands natively.

- Voice capture pipeline: browser MediaRecorder → Deepgram STT → Claude intent classifier → agent routing
- `voice_intent.py` already built and tested — integration with browser mic is the gap
- ElevenLabs TTS for spoken responses (Chief reads the brief to you)
- Voice shortcuts: "How's my recovery?" → routes to Pulse without typing

### Phase 2: Email Intelligence Live

**Goal:** Email Intelligence Engine running live, validated, surfaced in UI.

Remaining work:
- [ ] Build Subscription Cleanup UI in `/settings` (batch unsubscribe flow)
- [ ] Build Case Management UI (case list, case detail, timeline view, mark resolved)
- [ ] Surface cases on `/today` page (high-priority cases in brief)
- [ ] Run case discovery live on Mohamed's inbox — validate quality
- [ ] Test `run_cross_entity_reasoning` end-to-end with real cases
- [ ] Connect Initial Interview flow: post-scan → Echo presents findings → RL feedback stored

### Phase 3: Finance Connectors

**Goal:** Ledger has real transaction data.

- Integrate Tink (European bank API) or Plaid (broader coverage) for bank data
- Sync transactions → `lg_finance` table
- Ledger can answer: "What am I spending on food?", "Which subscriptions can I cancel?"
- Subscription detection via real transaction patterns (not just email detection)
- Budget vs actual spend tracking

### Phase 4: Mobile App

**Goal:** Chief on your phone. Voice-first.

- React Native (Expo) app
- Push notifications for proactive alerts (declining recovery, stalled case)
- Voice-first interface — default to speaking
- Quick capture: voice note → routed to correct agent + stored in Life Graph
- Widgets: Momentum Score ring on home screen

### Phase 5: Multi-User & Co-Founder Workspaces

**Goal:** Chief for teams.

- Co-founder workspaces — shared Life Graph segments
- Brand contexts — Chief understands "for the Lumina launch" vs "for my personal goals"
- Shared approval queue for team actions
- Delegate commitments between workspace members

### Near-Term Backlog (next 2 weeks)

Priority order:

1. **Connect GitHub PAT** → Forge gets real commit velocity for current projects
2. **Connect WHOOP credentials** → Pulse gets real recovery/sleep data
3. **Build subscription cleanup UI** → surface 34 detected subscriptions, batch unsubscribe
4. **Build case management UI** → case list page, case detail with timeline
5. **Add case-aware context to `/today`** → high-priority cases in morning brief
6. **Run case discovery live** → validate results, capture first RL signals from Mohamed
7. **Deploy agent service** → currently localhost only, needs hosting (Railway/Render/Fly)

---

## 16. Jarvis Analysis — Competitor Study

**Repository:** Personal AI assistant by Robert Netzke. License: RSALv2 (reference-only — no code copying permitted or performed).

**What was studied:** Architecture patterns, schema design, agent hierarchy concepts.

**What was independently reimplemented in Chief:**

| Pattern | Jarvis original | Chief implementation |
|---------|----------------|---------------------|
| Authority engine | TypeScript, single-user, SQLite | Python, multi-user, Postgres + RLS |
| `[AWAITING_APPROVAL]` deferred execution | In-memory state | `approval_queue` table, persistent |
| Agent hierarchy with authority levels | TypeScript `AgentNode` | Python `AgentNode` in `hierarchy.py`, Postgres `agent_messages` |
| Role YAML configs | YAML per agent | Python dataclasses in `hierarchy.py` |
| Knowledge graph schema | SQLite entities/facts/relationships | Postgres tables + pgvector + RLS |
| `approval_patterns` learning | Not in Jarvis | Chief addition: auto-approve after 5 consecutive approvals |
| `recent_objects` LRU (50 cap) | API-layer enforcement | DB trigger `trg_trim_recent_objects` |

**Chief advantages over Jarvis:**

| Dimension | Jarvis | Chief |
|-----------|--------|-------|
| Health data | None | WHOOP connector (recovery, sleep, workouts) |
| Financial data | Plaid on distant roadmap | Phase 3 (Tink/Plaid) |
| Email intelligence | None | 5-layer model, case discovery, 52K emails processed |
| Momentum Score | None | Cross-domain composite with 7-day history |
| Multi-user SaaS | Single-user by design | Multi-user with full RLS isolation |
| Mobile | Desktop/voice only | React Native Phase 4 |
| Deployment | Local only | Web-deployed (Next.js + Supabase + Python service) |
| RL feedback loop | Basic | email_feedback + approval_patterns tables |

---

## 17. Key Decisions Made

### Decision 1: Architecture — Next.js + Supabase + Python FastAPI

**Why not full TypeScript?** Python has vastly better ML/AI tooling (PydanticAI, Bedrock SDK, sentence-transformers). The intelligence layer needs Python. Next.js handles the UI and server-side API routes efficiently. Supabase handles auth, realtime, storage, and RLS without custom infrastructure.

**Why Supabase over raw Postgres?** Auth (OAuth out of the box), realtime (approval queue live updates), storage (document uploads), and the GitHub integration for auto-applying migrations. Zero-config infrastructure.

### Decision 2: LLM — Amazon Bedrock eu-central-1

User already has AWS credentials. Bedrock is approximately 40% cheaper than direct Anthropic API at the same model quality. EU region required for GDPR compliance (user data stays in eu-central-1). Model IDs: `eu.anthropic.claude-haiku-4-5-20251001-v1:0` and `eu.anthropic.claude-sonnet-4-6-20251231-v1:0`.

### Decision 3: Model Split — Haiku for Routing, Sonnet for Synthesis

Haiku is sufficient for: message routing, entity classification, simple factual agent responses. Sonnet is required for: morning brief (complex synthesis), Echo (nuanced email handling — Haiku over-refuses), case discovery (multi-email situation analysis), document OCR. The split keeps costs low while maintaining quality where it matters.

### Decision 4: Package Name — `email_intelligence` (not `email`)

`email` conflicts with Python's standard library. Discovered during implementation. Named `email_intelligence` throughout.

### Decision 5: Auth Strategy

Supabase email+password + Google OAuth as primary flows. Magic link as fallback. GitHub OAuth for developer users. All OAuth redirect URLs must be registered: `http://localhost:3000/callback` and `http://localhost:3002/callback` (port 3002 when 3000 is occupied).

### Decision 6: Onboarding — 3-Step Wizard, Then Real Data Only

No stub data. User zero (Mohamed) is also the real user. Every piece of data in the system is real from day 1. This means some pages show empty states until connectors are configured — acceptable tradeoff for authenticity over demo mode.

### Decision 7: Design System — Lumina V2 Ported

The Lumina marketing site design system (dark premium, violet/indigo primary, Inter + Geist fonts) was adapted for Chief's UI. This ensures visual consistency between the two projects (Chief and Lumina are part of the same founder's portfolio) and saves design iteration time.

### Decision 8: Approval Queue as Trust Foundation

The approval queue pattern is the core trust mechanism. Everything consequential goes through it. This is non-negotiable:
- Sending an email → approval queue
- Cancelling a subscription → approval queue
- Unsubscribing from a newsletter → approval queue
- Drafting a document reply → approval queue

The audit trail is populated regardless of decision. Trust is built through transparency and reversibility.

### Decision 9: Voice Intent — Adapted from Jarvis Classifier

The voice intent classifier structure was inspired by Jarvis's intent routing approach, but implemented independently in Python for Chief's 7-domain architecture. The classifier produces a `VoiceIntent` model: `{agent, confidence, action, entities[], domain}`.

### Decision 10: No Database Triggers for Business Logic (Except LRU Cap)

Business logic lives in Python, not in DB triggers. Exception: `trg_trim_recent_objects` (caps LRU at 50 per user — a pure data constraint) and `trg_commitments_updated_at` (auto-updates `updated_at` timestamp). Keeping logic in Python makes it testable, debuggable, and moveable.

---

## 18. Co-Founder Context

Chief is being built by **Mohamed Sherbini** (user zero and primary developer) with co-founders.

**The Lumina Connection:** Chief reuses the Lumina V2 design system (dark premium, violet/indigo palette). Lumina is the marketing/SaaS site being built in parallel in `C:/Users/Micha/lumina`. Both projects share visual identity and some component patterns.

**The Amazon Bedrock Decision:** Mohamed is already on Bedrock for personal use. The Chief internal agents use `AnthropicBedrock` client (`eu.anthropic.*` model IDs, eu-central-1 region). This is both cheaper and EU-compliant.

**Dev Environment:**
- Terminal 1: `cd apps/web && npm run dev` (port 3002 if 3000 is taken)
- Terminal 2: `cd services/agents && .venv/Scripts/python.exe -m uvicorn main:app --reload --port 8001`
- Test: `cd services/agents && .venv/Scripts/python.exe -m pytest tests/ -v`
- Eval: `cd services/agents && .venv/Scripts/python.exe -m eval.runner`

**Supabase GitHub Integration:**
- Connected to `MSherbinii/ChiefAI`
- Migrations in `supabase/migrations/` are auto-applied on push to master
- No manual migration runs needed — push the SQL file, it deploys

**Dev credentials (dev only, not production):**
- Supabase project: `hjuanwztmwbwjzoquxtl`
- Dev auth: `sherbini2002@gmail.com` / `Chief2026!`
- Magic link and OAuth also supported

---

*Document generated 2026-05-28 from live codebase. 63 commits. 137 tests passing. 66 Python files. 70 TypeScript files.*
