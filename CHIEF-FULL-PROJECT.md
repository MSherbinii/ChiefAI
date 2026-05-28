# CHIEF — Complete Project Document
*Personal Life OS | May 2026 | Status: Active Development*

---

## 1. What Chief Is

### The Problem: Context Fragmentation

Modern life runs across 15+ disconnected tools: Gmail (52,459 emails, 87 active cases), WHOOP (recovery data), GitHub (commits, velocity), Google Calendar (deadlines), bank apps (subscriptions, spending), Supabase docs, insurance portals, government letter PDFs. None of these talk to each other. The result: a salary didn't arrive in April/May 2025 — and you noticed it by accident weeks later. A debt collection case (FitStar, Aktenzeichen 5284-26-02-0189-0) escalated through two companies before surfacing. Deutsche Bahn passenger rights claims (24V15535046, 24V12495149) sat stalled for 10+ months. These are not edge cases. This is modern life operating at a constant 30% deficit because no single tool has the full picture.

### The Solution: Unified Intelligence Layer + Proactive Agents

Chief is a personal life operating system. It ingests data from every domain, stores a structured Life Graph (entities, facts, relationships), runs 7 specialized sub-agents, and surfaces what actually matters — without being asked. The architecture has two modes:

1. **Reactive**: User asks a question → Chief routes to the right specialist → specialist answers with real data from the Life Graph.
2. **Proactive**: Background scanner (runs every 4 hours) detects health anomalies, stale communications, velocity drops, cross-domain conflicts, and queues items for user approval.

### The Promise: "Your life feels under management"

Not productivity software. Not a chatbot. A genuine operating layer: Morning Brief at 7am, Momentum Score tracking week-over-week progress, an approval queue where every consequential action waits for user sign-off before execution, and an email intelligence engine that doesn't just read your inbox — it understands what's happening across 52,459 emails and tells you which 87 situations need your attention.

### Current Status (May 2026)

- Gmail OAuth connected, 52,459 emails deep-scanned
- 339 entities clustered (Haiku classification)
- 34 active subscriptions detected
- 87 email cases discovered autonomously
- 7 agents live and routing on Bedrock eu-central-1
- Morning Brief auto-generated daily (cron 07:00)
- Momentum Score with 7-day sparkline
- 137 tests passing, 5.00s runtime
- Approval queue with RL feedback loop
- Auth + onboarding complete (3-step wizard)
- Frontend: Next.js 15, all pages live

---

## 2. Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  User (browser / voice)                                         │
└──────────────────────┬──────────────────────────────────────────┘
                       │ HTTP
┌──────────────────────▼──────────────────────────────────────────┐
│  Next.js 15 App Router  (apps/web, port 3002)                   │
│  /today  /chat  /domains  /graph  /settings  /replay            │
│  /onboarding  /login  /callback                                 │
└──────┬────────────────────────────────────┬──────────────────────┘
       │ REST /api/* (Next.js route handlers)│
       │                                    │ Supabase JS client
┌──────▼──────────────────────┐    ┌────────▼──────────────────────┐
│  FastAPI Agent Service       │    │  Supabase (Postgres + pgvector)│
│  (services/agents, port 8001)│    │  Project: hjuanwztmwbwjzoquxtl │
│                              │    │  29 tables, RLS on all         │
│  orchestrator.py             │    │  Auto-migrations on git push   │
│  ├─ Routing (Haiku/GLM)      │◄───┤  to MSherbinii/ChiefAI        │
│  ├─ 7 agents                 │    └────────────────────────────────┘
│  ├─ guardrails.py            │
│  ├─ memory.py                │    ┌────────────────────────────────┐
│  ├─ proactive.py             │    │  Amazon Bedrock eu-central-1   │
│  ├─ feedback.py              │    │  AnthropicBedrock client        │
│  ├─ hierarchy.py             │───►│  boto3 Converse API (non-Anth) │
│  ├─ email_intelligence/      │    │  Titan Embeddings v2 (1024d)   │
│  └─ connectors/              │    └────────────────────────────────┘
└──────────────────────────────┘
```

### Intelligence Agnosticism Principle

Chief is provider-agnostic and data-agnostic by design. The `llm.py` factory returns either `anthropic.AnthropicBedrock` (when AWS credentials present) or `anthropic.Anthropic` (fallback). Non-Anthropic models (Qwen, GLM, Nova) use `boto3.client('bedrock-runtime').converse()`. Model IDs are all env-var overridable (`CHIEF_ROUTING_CHEAP`, `CHIEF_AGENT_MODEL`, `CHIEF_BRIEF_MODEL`). The system can switch from Haiku to Qwen3 32B with a single env var change.

Data agnosticism: every domain writes to the same Life Graph schema (entities, facts, relationships). WHOOP writes to `lg_health`. GitHub writes to `lg_projects` + `facts`. Gmail writes to `lg_communications` + `email_raw` + `email_cases`. Whether you switch banks, email clients, or fitness trackers — the graph persists.

### Full Stack

| Layer | Technology | Details |
|-------|-----------|---------|
| Frontend | Next.js 15 App Router | TypeScript, Tailwind CSS, Supabase JS |
| Backend | Python FastAPI + APScheduler | uvicorn, port 8001, async |
| Database | Supabase (Postgres 15 + pgvector) | hjuanwztmwbwjzoquxtl, eu-central-1 |
| LLM | Amazon Bedrock eu-central-1 | anthropic SDK + boto3 Converse API |
| Embeddings | Amazon Titan Embeddings v2 | 1024 dims, padded to 1536 for pgvector |
| Auth | Supabase magic link + email/password | dev: sherbini2002@gmail.com |
| CI/DB | Supabase GitHub Integration | auto-applies migrations on push to master |
| Monorepo | chief/ with apps/web + services/agents | no workspace tooling, simple structure |

---

## 3. LLM Models & Costs

### Active Model Configuration

```python
# llm.py — current defaults (all overridable via env vars)

ROUTING_MODEL_CHEAP = 'zai.glm-4.7-flash'         # ~50x cheaper than Haiku ✅ tested
AGENT_MODEL_CHEAP   = 'qwen.qwen3-32b-v1:0'       # ~10x cheaper than Haiku ✅ available

ROUTING_MODEL = 'eu.anthropic.claude-haiku-4-5-20251001-v1:0'       # current default routing
AGENT_MODEL   = 'eu.anthropic.claude-haiku-4-5-20251001-v1:0'       # current default agents
BRIEF_MODEL   = 'eu.anthropic.claude-sonnet-4-5-20250929-v1:0'      # Brief + Echo + Cases
```

### Available on Bedrock eu-central-1 (Full Catalogue)

**Ultra-Cheap (routing / classification)**
- `zai.glm-4.7-flash` — Z.AI GLM-4 Flash, ~50x cheaper than Haiku, tested ✅
- `eu.amazon.nova-micro-v1:0` — Amazon Nova Micro, ~20x cheaper than Haiku
- `meta.llama3-2-3b-instruct` — Meta Llama 3.2 3B, ~100x cheaper
- `meta.llama3-2-1b-instruct` — Meta Llama 3.2 1B

**Cheap + Capable (agent responses)**
- `eu.amazon.nova-lite-v1:0` — Amazon Nova Lite, ~5x cheaper than Haiku
- `qwen.qwen3-32b-v1:0` — Alibaba Qwen3 32B, ~10x cheaper than Haiku ✅ available
- `eu.anthropic.claude-haiku-4-5-20251001-v1:0` — Claude Haiku 4.5 (current default)

**Quality (synthesis, case discovery, Echo)**
- `qwen.qwen3-235b-a22b-2507-v1:0` — Alibaba Qwen3 235B MoE, ~3x cheaper than Sonnet
- `qwen.qwen3-coder-30b-a3b-v1:0` — Alibaba Qwen3 Coder 30B
- `eu.anthropic.claude-sonnet-4-5-20250929-v1:0` — Claude Sonnet 4.5 (current Brief/Echo)
- `eu.anthropic.claude-sonnet-4-6-20251231-v1:0` — Claude Sonnet 4.6 (newest, available)

**Premium (complex reasoning)**
- `eu.anthropic.claude-opus-4-5-20250929-v1:0` — Claude Opus 4.5
- `eu.anthropic.claude-opus-4-6-20251231-v1:0` — Claude Opus 4.6
- `eu.anthropic.claude-opus-4-7-20260101-v1:0` — Claude Opus 4.7

**Other**
- `eu.amazon.nova-pro-v1:0` — Amazon Nova Pro
- `eu.amazon.nova-2-lite-v1:0` — Amazon Nova 2 Lite
- `mistral.devstral-2-123b-v1:0` — Mistral Devstral 2 123B
- `mistral.pixtral-large-v1:0` — Mistral Pixtral Large (vision)
- `openai.gpt-oss-120b-v1:0` — OpenAI GPT OSS 120B
- `openai.gpt-oss-20b-v1:0` — OpenAI GPT OSS 20B

### Cost Analysis

| Scenario | Models | Est. $/user/day |
|---------|--------|-----------------|
| Current (all Haiku + Sonnet Brief) | Haiku + Sonnet | ~$0.13 |
| Routing → GLM Flash, Agents → Qwen3 32B | GLM + Qwen3 + Sonnet | ~$0.02-0.03 |
| Full cheap stack | GLM + Nova Lite + Qwen3 235B | ~$0.01 |

Switch command:
```bash
export CHIEF_ROUTING_CHEAP=zai.glm-4.7-flash
export CHIEF_AGENT_MODEL=qwen.qwen3-32b-v1:0
export CHIEF_BRIEF_MODEL=qwen.qwen3-235b-a22b-2507-v1:0
```

---

## 4. The 7 Agents

### Chief (Orchestrator)
- **authority_level**: 10 (highest — cross-domain synthesis, no domain restriction)
- **model**: `BRIEF_MODEL` (Sonnet) — cross-domain synthesis requires broad reasoning
- **reads**: all Life Graph tables, entire conversation history, agent messages
- **routing keywords**: "anything else", general questions, cross-domain, strategy, planning, overall summary, today focus
- **status**: Live. Handles unrouted queries and multi-agent synthesis.
- **system prompt emphasis**: Integrates health + work + finance + admin context simultaneously. Delegates to specialists when appropriate.

### Pulse (Health)
- **authority_level**: 4
- **model**: `AGENT_MODEL` (Haiku)
- **reads**: `lg_health` (WHOOP recovery scores, sleep stages, HRV, workouts), nutrition logs
- **routing keywords**: health, fitness, sleep, recovery, gym, nutrition, food, weight, injury
- **status**: Live. WHOOP OAuth connector built, awaiting PAT from developer.whoop.com to activate live sync. Currently serves from `lg_health` data if seeded manually.
- **tools**: `get_health_summary`, `get_sleep_data`, `get_workout_history`, `check_recovery`

### Echo v2 (Email / Cases)
- **authority_level**: 5
- **model**: `BRIEF_MODEL` (Sonnet) — Haiku over-refuses email access, Sonnet required
- **reads**: `email_cases` (87 active cases), `email_raw` (52,459 emails), `lg_communications`
- **routing keywords**: emails, communication, inbox, cases, situations, stalled, urgent, congstar, fitstar, 1&1, deutsche bank, salary, landlord, dispute, mahnung, forderung, inkasso, debt, case, "what is going on with", "what happened with", "what is stalled", pending reply, follow-up, thread, draft, professor, reply, message
- **status**: Live. Echo v2 queries `email_cases` first for structured case context before falling back to raw email threads.
- **CASE_QUERY_KEYWORDS**: dispute, mahnung, forderung, inkasso, debt, stalled, pending, escalated, urgent, case, aktenzeichen, situation, problem, issue
- **context injection**: Case timeline is injected as assistant message prefix so Sonnet sees full case history without needing tool calls.

### Forge (Projects / Work)
- **authority_level**: 4
- **model**: `AGENT_MODEL` (Haiku)
- **reads**: `lg_projects` (GitHub repos, thesis), `commitments` (deadlines), `facts` (commit velocity), `lg_goals`
- **routing keywords**: thesis, GitHub, code, project, task, startup, deadline, commit, work, velocity, repositories
- **status**: Live. GitHub connector built (`connectors/github.py`), awaiting GitHub PAT for live sync. Calendar events sync to `commitments`.
- **tools**: `get_project_status`, `get_recent_commits`, `get_deadlines`, `check_velocity`

### Ledger (Finance)
- **authority_level**: 6 (higher than Pulse/Forge — financial data sensitivity)
- **model**: `AGENT_MODEL` (Haiku)
- **reads**: `lg_finance` (spending, subscriptions, transactions), `email_subscriptions` (34 detected)
- **routing keywords**: spending, bank, balance, subscription, afford, budget, money, transaction, financial, cost, price, invoice, receipt, "kann ich mir leisten"
- **status**: Live for read queries. No bank connector yet — Tink integration planned Phase 2. Subscription data comes from email intelligence engine.
- **tools**: `get_spending_summary`, `list_subscriptions`, `check_affordability`, `get_transactions`

### Clerk (Admin / Bureaucracy)
- **authority_level**: 5
- **model**: `AGENT_MODEL` (Haiku)
- **reads**: `lg_documents` (insurance cards, contracts, letters via OCR), `facts` (German admin data), `approval_queue`
- **routing keywords**: insurance, letter, bureaucracy, form, appointment, TK, AOK, Beitragsnummer, visa, residence, document, contract, German admin, government, Anmeldung, Abmeldung
- **status**: Live. Claude Vision OCR pipeline (`document_extractor.py`) extracts structured fields from uploaded documents. Handles German bureaucracy context.
- **tools**: `get_document_summary`, `find_insurance_info`, `get_form_status`, `lookup_deadline`

### Scout (Research)
- **authority_level**: 3 (lowest — research only, no personal data writes)
- **model**: `AGENT_MODEL` (Haiku)
- **reads**: external (web research), `facts` (prior research stored in graph), `lg_goals`
- **routing keywords**: research, compare, find, look up, market, competitive, travel, course, German, regulation, alternatives, recommendation
- **status**: Live. Web search not yet wired — currently uses knowledge graph facts + LLM knowledge. Web connector planned Phase 1B.
- **tools**: `search_web`, `compare_options`, `summarize_topic`, `find_courses`

### Routing Flow

```
User message
    │
    ▼
voice_intent? (pre-classified) ──► skip Haiku routing
    │ no
    ▼
ROUTING_MODEL (Haiku or GLM Flash)
    │ → "Echo" / "Pulse" / "Forge" / etc.
    ▼
check_input_guardrails(message, agent_name)
    │ fail → return Chief fallback
    ▼
get_recent_context(user_id, agent_name)  [memory]
    │
    ▼
agent.handle(request)
    │
    ▼
check_output_guardrails(reply)
    │
    ▼
evaluate_response_quality(0-100 score)
    │
    ▼
save_interaction(memory) + save_quality_feedback
    │
    ▼
ChatResponse { reply, agent, confidence }
```

---

## 5. Email Intelligence Engine v2 (The Big Feature)

### Problem with the Old Approach

The original email connector fetched 50 threads via the Gmail API and handed them directly to Echo. This was useless: 50 threads out of 52,459 is a random sample with no prioritization, no understanding of ongoing situations, no connection between related emails from different senders about the same issue.

### The 5-Layer Model

```
Layer 1: email_raw         — full inbox store, 52,459 emails, all fields
Layer 2: entities           — 339 companies/people clustered by domain (Haiku)
Layer 3: email_cases        — 87 active situations discovered by Sonnet
Layer 4: email_subscriptions — 34 recurring senders, engagement scores
Layer 5: email_feedback     — RL training signal from user corrections
```

### Plan A (Complete): Infrastructure + Deep Scan

1. **Deep Scan** (`connectors/gmail.py` → `email_intelligence/`): Full Gmail inbox pagination via `users.messages.list` with `pageToken`. All 52,459 messages fetched in batches of 500, stored to `email_raw` with full body text, labels, threading metadata.
2. **Entity Clustering** (`email_intelligence/clusterer.py`): Groups emails by `from_email` domain. Haiku classifies each cluster into one of: `service_provider`, `bank`, `debt_collector`, `employer`, `professor`, `newsletter`, `marketplace`, `government`, `friend`, `unknown`. Results stored in `entities` table with `relationship_type`, `email_domains[]`, `interaction_count`, `engagement_score`.
3. **Subscription Detection** (`email_intelligence/subscription_detector.py`): Pattern-matches for `List-Unsubscribe` headers, calculates average interval between emails, computes engagement score (open_rate × reply_rate). 34 subscriptions detected with engagement scores.

### Plan B (Complete): Case Discovery + Lifecycle

1. **Case Discovery** (`email_intelligence/case_discoverer.py`): Sonnet analyzes each entity's email thread corpus. For each entity with >3 emails: extracts ongoing situations, assigns status (`open`/`progressing`/`stalled`/`needs_action`), priority (`critical`/`high`/`normal`/`low`), `pending_action`, and a `timeline` array of key events. Results stored in `email_cases`.
2. **Cross-Entity Reasoner** (`email_intelligence/cross_entity_reasoner.py`): Sonnet analyzes pairs of entities for escalation patterns (company A → debt collector B), shared reference numbers, temporal adjacency. Auto-merges linked cases.
3. **Pattern Scanner** (`email_intelligence/pattern_scanner.py`): Zero-shot pattern detection across all emails regardless of entity classification. Detects dispute/billing/legal patterns by subject line + keyword analysis. Creates cases from patterns without entity pre-classification.
4. **Lifecycle Rules** (`email_intelligence/case_discoverer.py:apply_lifecycle_rules`): Auto-archives cases older than 90 days with no activity. Demotes stalled cases.

### The Agentic Pipeline (Latest, Most Correct)

`email_intelligence/agentic_pipeline.py` — `run_agentic_pipeline(user_id)`:

```
Step 1: Entity Graph Builder
  - Paginate ALL 52,459 emails (not just top entities)
  - Group by sender domain
  - For each group: extract company name, relationship_type, all Aktenzeichen
  - _extract_references() handles formats:
      · "Aktenzeichen: 5284-26-02-0189-0"
      · "Az. 12345/2025"
      · "Referenz: ABC-123"
      · space-separated variants (e.g. "Az 5284 26 02 0189 0")

Step 2: Cross-Entity Relationship Inference (Sonnet)
  - Given full entity graph, identify:
      · Temporal adjacency (company stops emailing → collector starts)
      · Shared reference numbers across entities
      · Escalation chains (provider → legal → bailiff)
  - Output: linked_entities[] per case

Step 3: Zero-Shot Situation Detection (Sonnet)
  - For each entity/cluster: "What ongoing situations exist?"
  - No pre-defined categories
  - Output: email_cases rows with confidence scores

No manual intervention ever. Pipeline is fully autonomous.
```

### Real Cases Discovered (Autonomously)

| Case | Priority | Status | Details |
|------|---------|--------|---------|
| FitStar Debt Collection | CRITICAL | needs_action | Aktenzeichen 5284-26-02-0189-0. Two collectors: kohlkg.com + einfach-klaeren.de. Cross-entity escalation detected. |
| Congstar Billing | RESOLVED | resolved | €100/month installment plan. System was sending redundant payment emails. Marked resolved after user confirmation. |
| Deutsche Bahn Passenger Rights | HIGH | stalled | Two claims: 24V15535046 + 24V12495149. Stalled 10+ months. Pending action: follow-up email. |
| Missing Salary Apr/May 2025 | HIGH | needs_action | No salary deposit detected for April or May 2025. Pending action: contact employer. |
| Anmeldung / Municipal Registration | HIGH | stalled | Landlord requiring municipal registration. 135 days stalled. Pending action: contact landlord. |

### RL Feedback Loop

Every user interaction with a case generates an `email_feedback` record:
- `case_confirm` → confidence boost
- `case_reject` → case marked resolved, confidence 0.1
- `case_merge` → two cases unified
- `entity_correct` → relationship_type updated immediately
- `context_injection` → user note stored, future discovery uses it
- `priority_change` → priority updated

Echo v2 uses the feedback loop to improve case quality over time without retraining.

---

## 6. Database Schema (All 29 Tables)

### Core / Auth
| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `profiles` | Extends auth.users | `display_name`, `timezone` (Europe/Berlin default) |

### Life Graph
| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `lg_people` | People in user's life | `name`, `relationship`, `importance (1-5)`, `embedding vector(1536)` |
| `lg_projects` | Projects and repos | `name`, `type`, `status`, `deadline`, `tools[]`, `embedding` |
| `lg_health` | Health metrics | `metric`, `value jsonb`, `source`, `confidence`, `recorded_at` |
| `lg_finance` | Financial records | `account`, `type`, `amount_cents`, `currency`, `is_subscription`, `recurring_period` |
| `lg_communications` | Email threads | `thread_id`, `channel`, `participants[]`, `summary`, `staleness_days`, `urgency` |
| `lg_documents` | Uploaded docs | `type`, OCR fields, `storage_path` |
| `lg_goals` | User goals | `title`, `category`, `target`, `progress`, `deadline` |

### Intelligence Layer
| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `entities` | Clustered real-world entities | `name`, `type`, `relationship_type`, `email_domains[]`, `interaction_count`, `engagement_score`, `first_contact`, `last_contact`, `embedding vector(1536)` |
| `facts` | Knowledge graph facts | `subject_entity_id`, `predicate`, `object`, `confidence`, `source`, `embedding` |
| `relationships` | Entity-entity edges | `from_entity_id`, `to_entity_id`, `type`, `strength` |

### Email Intelligence
| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `email_raw` | Full inbox store | `gmail_id`, `thread_id`, `from_email`, `subject`, `body_text`, `date`, `labels[]`, `is_read`, `embedding vector(1536)` |
| `email_cases` | Active situations | `title`, `status (open/progressing/stalled/needs_action/resolved)`, `priority (low/normal/high/critical)`, `category`, `summary`, `entities uuid[]`, `pending_action`, `stalled_since`, `timeline jsonb`, `confidence`, `user_notes` |
| `email_subscriptions` | Newsletter/recurring | `sender_email`, `frequency`, `avg_interval_days`, `total_received`, `engagement_score`, `unsubscribe_url`, `user_decision` |
| `email_feedback` | RL training signal | `feedback_type (case_confirm/case_reject/case_merge/entity_correct/priority_change/action_approve/action_reject)`, `target_id`, `target_type`, `old_value jsonb`, `new_value jsonb` |
| `email_scan_status` | Scan progress | `status (idle/scanning/clustering/detecting_subscriptions/complete/error)`, `total_emails`, `scanned_emails`, `error_message` |

### Agent Operations
| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `approval_queue` | Agent actions awaiting user sign-off | `agent`, `action_type`, `risk_level`, `title`, `description`, `payload jsonb`, `context_capsule jsonb`, `status (pending/approved/rejected)` |
| `audit_trail` | Every tool call logged | `agent`, `tool_name`, `action_category`, `authority_decision`, `executed`, `execution_time_ms`, `input_data`, `output_data` |
| `approval_patterns` | Auto-approve learning | `agent`, `action_category`, `tool_name`, `consecutive_approvals`, `auto_approve bool` |
| `agent_quality_log` | Response quality scores | `agent`, `user_message`, `response_preview`, `quality_score (0-100)`, `pass bool` |
| `chat_messages` | Conversation memory | `user_id`, `agent`, `role`, `content`, `created_at` |
| `commitments` | Calendar and delegated tasks | `title`, `due_date`, `assigned_agent`, `status (AWAITING_APPROVAL/active/done)` |
| `agent_messages` | Inter-agent messages | `from_agent`, `to_agent`, `task`, `priority`, `status` |
| `recent_objects` | Recently accessed entities | `user_id`, `object_type`, `object_id`, `accessed_at` |

### Scoring / Reporting
| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `momentum_scores` | Daily Momentum Score | `user_id`, `score (0-100)`, `breakdown jsonb`, `date` |
| `briefs` | Morning Brief history | `user_id`, `content`, `best_move`, `generated_at` |
| `goal_check_ins` | Weekly Replay data | `goal_id`, `progress`, `notes`, `week_of` |

### Connectors
| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `connector_tokens` | OAuth tokens per connector | `user_id`, `connector (gmail/github/whoop/google_calendar)`, `access_token`, `refresh_token`, `sync_status (ok/error/pending)`, `last_synced_at` |

---

## 7. All API Endpoints (38 total)

### Core
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check |
| POST | `/chat` | Main chat endpoint — routes to agent, returns ChatResponse |
| POST | `/voice/classify` | Classifies voice transcript → VoiceIntent (agent + confidence) |

### Sync Connectors
| Method | Path | Description |
|--------|------|-------------|
| POST | `/sync/google` | Trigger async Gmail sync for user |
| POST | `/sync/github` | Trigger async GitHub sync for user |
| POST | `/sync/whoop` | Trigger async WHOOP sync for user |
| POST | `/sync/imap_uni` | Trigger async IMAP sync for university email |
| POST | `/sync/google_calendar` | Trigger async Google Calendar sync |

### Email Intelligence
| Method | Path | Description |
|--------|------|-------------|
| POST | `/email/deep-scan` | Full inbox scan → entity clustering → subscription detection (async pipeline) |
| GET | `/email/scan-status/{user_id}` | Get deep scan progress and status |
| GET | `/email/subscriptions/{user_id}` | List active subscriptions ordered by engagement score |
| GET | `/email/stats/{user_id}` | Email intelligence stats: total emails, entities, subscriptions, scan status |
| POST | `/email/cases/run-discovery` | Run case discovery + cross-entity reasoning (async) |
| GET | `/email/cases/{user_id}` | List active cases sorted by priority weight (critical→low) |
| GET | `/email/case/{case_id}` | Get full case details including timeline jsonb |
| POST | `/email/case/{case_id}/resolve` | User marks case resolved + stores RL feedback |
| POST | `/email/case/{case_id}/note` | Add user context note to case (context_injection RL signal) |
| POST | `/email/feedback` | Store RL feedback signal from user corrections |
| POST | `/email/cases/merge` | Merge two cases user identifies as same situation |
| POST | `/email/pattern-scan` | Pattern-first case discovery (dispute/billing/legal patterns) |
| POST | `/email/agentic-discovery` | Full agentic pipeline: entity graph → relationship inference → situation detection |
| POST | `/email/lifecycle` | Apply lifecycle rules: archive old, demote stale cases |
| GET | `/email/pattern-groups/{user_id}` | Preview email groups that triggered pattern detection |
| POST | `/email/unsubscribe` | Queue unsubscribe action in approval_queue |
| GET | `/email/present-cases/{user_id}` | Structured case summary for Echo's initial interview message |

### Intelligence and Scoring
| Method | Path | Description |
|--------|------|-------------|
| POST | `/score/momentum` | Calculate Momentum Score for user |
| POST | `/brief/generate` | Generate Morning Brief for user |
| POST | `/proactive/scan` | Trigger proactive background scan for user |
| POST | `/knowledge/extract` | Extract entities/relationships from emails + commits (async) |
| POST | `/embeddings/update` | Update entity + communication pgvector embeddings |

### Feedback and Learning
| Method | Path | Description |
|--------|------|-------------|
| POST | `/feedback/approval` | Record approval/rejection for queue item (RL signal) |
| GET | `/feedback/performance/{user_id}/{agent}` | Get agent performance metrics for user |

### Agent Hierarchy
| Method | Path | Description |
|--------|------|-------------|
| GET | `/hierarchy` | Get full agent hierarchy tree with authority levels |
| GET | `/hierarchy/tasks/{user_id}/{agent}` | Get pending tasks for a specific agent |
| POST | `/hierarchy/delegate` | Delegate task from one agent to another |

### Documents and Evaluation
| Method | Path | Description |
|--------|------|-------------|
| POST | `/documents/extract` | Claude Vision OCR: extract structured fields from uploaded document |
| POST | `/connectors/imap/verify` | Verify IMAP credentials (test connection) |
| POST | `/eval/run` | Run full agent evaluation suite, return quality report |

### Scheduled Jobs (APScheduler)
| Schedule | Job | Description |
|---------|-----|-------------|
| Every 4 hours | `run_proactive_scan_all_users` | Health anomalies, stale comms, velocity drops |
| Daily 07:00 | `run_daily_brief_for_all` | Momentum Score + Morning Brief for all connected users |

---

## 8. Frontend Pages

| Route | Description |
|-------|-------------|
| `/login` | Email/password + magic link. Supabase auth. Redirect to /today after auth. |
| `/onboarding` | 3-step wizard: (1) name + timezone, (2) roles (student/founder/employee), (3) focus goals. Creates `profiles` row. |
| `/today` | Morning Brief card + Momentum Score sparkline (7-day) + Approval Queue. Auto-generates brief on first visit via `/brief/generate`. BriefLoader animation while generating. |
| `/chat` | Multi-agent chat. Agent color badges (Pulse=green, Echo=blue, Forge=orange, Ledger=yellow, Clerk=purple, Scout=teal). Slash commands: `/brief`, `/score`, `/scan`. Voice input button → `/voice/classify`. |
| `/domains` | Tabs: Health / Work / Finance / Admin. Each tab queries Life Graph for real data. Health shows WHOOP metrics. Work shows GitHub velocity. Finance shows subscriptions. Admin shows documents. |
| `/graph` | Life Graph browser. Entity grid with type filters. Click entity → facts panel. Search bar → semantic search via pgvector. |
| `/settings` | Sections: (1) Profile, (2) Connectors with sync buttons + status indicators, (3) Document upload with drag-and-drop → `/documents/extract`, (4) Agent status panel. |
| `/replay` | Weekly Replay from `goal_check_ins` history. Shows goal progress week-over-week. |

---

## 9. Test Coverage (137 tests, 5.00s)

| Test File | Coverage Area | Key Tests |
|-----------|--------------|-----------|
| `test_agent_integration.py` | Full orchestration pipeline | Input guardrails (injection blocking, domain violation), output guardrails, quality scoring, routing to correct agent, feedback loop, all 7 agents instantiate |
| `test_api.py` | FastAPI endpoints | Health check, chat endpoint, sync endpoints, brief generation, feedback endpoints |
| `test_authority.py` | Agent hierarchy + authority | Authority level enforcement, delegation flow, AWAITING_APPROVAL status, task queuing |
| `test_case_discovery.py` | Email case pipeline | Case discovery from entity threads, case deduplication, lifecycle rules (archive/demote), cross-entity merge |
| `test_email_intelligence.py` | Email intelligence (19 tests) | Deep scan pagination, entity clustering, subscription detection, scan status updates, engagement scoring |
| `test_eval_framework.py` | Evaluation framework | Quality score calculation, pass/fail thresholds, eval runner structure |
| `test_gmail_helpers.py` | Gmail connector helpers | OAuth token refresh, thread parsing, label filtering, reference extraction (Aktenzeichen formats) |
| `test_momentum.py` | Momentum Score | Score calculation from multi-domain data, 7-day history, delta vs yesterday |
| `conftest.py` | Shared fixtures | JWT mock (service role), Supabase mock client, AWS credential mocks |

All tests run with mocked Supabase (no real DB calls) and mocked AWS credentials. Live LLM evaluation via `eval/runner.py` (separate, makes real Bedrock calls): 90% pass rate, 97.5/100 avg quality score.

---

## 10. What's Working vs Planned

### Working (Confirmed Active)

| Feature | Status |
|---------|--------|
| Gmail OAuth + token refresh | Working |
| Full inbox deep scan (52,459 emails) | Complete |
| Entity clustering (339 entities, Haiku) | Complete |
| Subscription detection (34 subs) | Complete |
| Case discovery (87 cases, Sonnet) | Complete |
| Cross-entity reasoning (escalation detection) | Complete |
| Pattern scanner (dispute/billing/legal) | Complete |
| Agentic pipeline (entity graph → relationships → situations) | Complete |
| Echo v2 (case-aware, Sonnet) | Live |
| All 7 agents routing correctly | Live |
| Morning Brief (auto-generate + scheduled 07:00) | Live |
| Momentum Score + 7-day sparkline | Live |
| Approval Queue + RL feedback loop | Live |
| Agent hierarchy + delegation | Live |
| Document upload + Claude Vision OCR (Clerk) | Live |
| Google Calendar sync → commitments | Live |
| pgvector semantic search (Life Graph) | Live |
| Input/output guardrails + quality scoring (0-100) | Live |
| PydanticAI structured outputs (Pulse, Echo, Forge) | Live |
| Auth + onboarding (3-step wizard) | Live |
| Cheap model support (GLM Flash, Qwen3 32B) | Available |

### Pending / In Progress

| Feature | Status | Notes |
|---------|--------|-------|
| WHOOP live sync | Pending | OAuth built, waiting for developer.whoop.com PAT |
| GitHub live sync | Pending | Connector built, waiting for GitHub PAT |
| Bank connectors (Tink) | Phase 2 | Tink EU API, German bank support |
| Subscription cleanup UI | Not started | UI to browse + unsubscribe from detected subscriptions |
| Case management UI | Not started | Full case browser with timeline, resolve/merge/note actions |
| Web search for Scout | Not started | External web connector needed |
| Mobile app | Phase 3 | React Native |
| Multi-user (co-founders) | Phase 4 | Chief Startup use case |
| Voice capture (real-time) | Phase 1B | Currently voice intent classification only |

---

## 11. Roadmap

### Phase 1B (Current Sprint)
- Switch routing to GLM Flash (50x cheaper), agents to Qwen3 32B (10x cheaper)
- Voice capture: real-time mic → transcript → intent → agent
- Scout web connector (Serper or similar)
- Subscription cleanup UI in /settings
- Case management UI tab in /domains (Admin)

### Phase 2: Finance
- Tink EU bank connector: read-only transactions, balance
- German bank support (Deutsche Bank, ING, Sparkasse)
- Ledger agent upgrades: budget tracking, subscription cancel automation
- Affordability queries with real balance data
- `lg_finance` populated from real transactions

### Phase 3: Mobile
- React Native app (iOS + Android)
- Push notifications for Morning Brief + approval queue alerts
- Voice-first interaction
- Offline-capable Life Graph cache

### Phase 4: Multi-User / Chief Startup
- Separate user contexts with shared team graph
- Co-founder visibility: who owns what, shared deadlines
- Bedrock cost splitting per user
- Admin panel for co-founder management
- Lumina design system reuse for Chief UI

---

## 12. Key Architectural Decisions

### Why Python + Next.js (not TypeScript monorepo)

Python is necessary for Amazon Bedrock SDK (`anthropic.AnthropicBedrock`), boto3 (Converse API for non-Anthropic models), pgvector operations, APScheduler background jobs, and the email intelligence pipeline. TypeScript lacks mature equivalents for this LLM + data pipeline stack. Next.js handles the frontend exclusively. The split is clean: Next.js API routes proxy to FastAPI for anything agent-related, handle OAuth callbacks, and serve the UI. No business logic in Next.js API routes beyond auth and proxying.

### Why Bedrock EU (cost + data residency)

- Data residency: all LLM calls stay in eu-central-1. Personal health, financial, email data never leaves EU.
- Cost: Bedrock on-demand pricing for Haiku is lower than Anthropic API at volume. Access to GLM Flash (~50x cheaper than Haiku) and Qwen3 32B (~10x cheaper) through the same boto3 Converse API.
- Model diversity: access to Amazon Nova, Meta Llama, Mistral, Qwen, Z.AI, and OpenAI OSS models through a single API endpoint without separate vendor contracts.

### Why Sonnet for Echo (not Haiku)

Haiku over-refuses email access. When given raw email thread content containing personal information (names, amounts, account numbers), Haiku refuses to engage citing privacy concerns — even when the user explicitly owns the data. Sonnet processes email content correctly without false-positive refusals. The cost increase is justified: Echo is the highest-value agent (87 cases discovered, direct financial and legal exposure).

### Why Agentic Pipeline > Entity-First

The initial entity-first approach (cluster entities → analyze each entity's threads → discover cases per entity) misses cross-entity situations. The FitStar case involves two separate companies (kohlkg.com, einfach-klaeren.de) that would appear as unrelated entities. The debt escalation only becomes visible when you look at temporal adjacency: FitStar stops emailing → kohlkg.com starts → einfach-klaeren.de starts. The agentic pipeline builds the full entity graph first, then uses Sonnet for cross-entity relationship inference, then zero-shot situation detection. This catches escalation chains that entity-siloed discovery cannot.

### Why Approval Queue for Everything

Trust and reversibility. An agent that can send emails, cancel subscriptions, or file forms without user sign-off is dangerous. The approval queue (with `AWAITING_APPROVAL` status) means every consequential action — regardless of the agent's confidence — gets human sign-off before execution. This also enables the RL feedback loop: every approval or rejection is a training signal. After N consecutive approvals for the same action type, the pattern is flagged for potential auto-approve. Auto-approve is never assumed; it requires explicit user enablement.

### Why pgvector (not Pinecone/Weaviate)

Supabase already hosts the Postgres instance. Adding pgvector keeps everything in one database with the same RLS policies, no separate vector DB credentials, no additional latency hop, and simpler backups. Titan Embeddings v2 produces 1024-dim vectors, padded to 1536 for the existing pgvector schema (no re-migration needed). Semantic search over the Life Graph and email corpus is fast enough at current scale (339 entities, 52k emails with embeddings being generated progressively).

---

## 13. Jarvis Analysis

**License**: RSALv2 — no code copying. All patterns independently reimplemented.

### Patterns Independently Reimplemented

| Jarvis Pattern | Chief Implementation | Location |
|---------------|---------------------|---------|
| Authority engine | `authority_level` int (1-10) per agent, `AWAITING_APPROVAL` status | `hierarchy.py`, `AGENT_HIERARCHY` dict |
| AWAITING_APPROVAL status | `approval_queue` table + `commitments.status` | `models.py`, `hierarchy.py` |
| Role YAML configs | Agent classes with `name`, `domain`, `authority_level`, `system_prompt` | `agents.py` |
| Agent hierarchy | `AGENT_HIERARCHY = {Chief: {level:10}, Pulse: {level:4}, ...}` | `hierarchy.py` |
| Knowledge graph schema | `entities` + `facts` + `relationships` tables with pgvector | `migrations/20260526000005_entities_facts.sql` |
| Audit trail | Every tool call logged pre/post execution | `audit_trail` table |
| Commitment tracking | `commitments` table with agent assignment + AWAITING_APPROVAL | `migrations/20260526000010_jarvis_inspired_tables.sql` |

### Where Chief Wins vs Jarvis

| Dimension | Jarvis | Chief |
|-----------|-------|-------|
| Health data | No real integration | WHOOP OAuth (pending PAT), Apple Health planned |
| Finance | No bank connectors | Tink planned, subscription data from email now |
| Multi-user | Single user | Phase 4: co-founders, team graph |
| Email depth | Basic email reading | 52,459 emails, 87 cases, 339 entities, RL loop |
| German bureaucracy | Not specialized | Clerk agent specialized for German admin context |
| Cost | Anthropic API only | Bedrock EU: GLM Flash, Qwen3, Nova — 10-100x cheaper |
| SaaS path | No | Chief Startup use case in MEMORY.md |

---

## 14. Security

### Row Level Security

RLS enabled on every table. All `select/insert/update/delete` policies use `auth.uid() = user_id`. No cross-user data access possible at the database layer.

### Service Role Isolation

The Python FastAPI service uses `SUPABASE_SERVICE_ROLE_KEY` (bypasses RLS) exclusively. This key is never exposed to the browser — it lives only in `services/agents/.env`. Next.js uses the anon key (RLS enforced). All agent operations go through FastAPI with the service role, which means RLS bypass is controlled and centralized.

### Approval Gate

All consequential actions — email drafting, unsubscribes, document filings, calendar events — are queued in `approval_queue` with `status: 'pending'`. The agent never executes a write action directly. The frontend shows pending items; the user approves or rejects. Execution only happens post-approval.

### Audit Trail

Every tool call (whether approved, rejected, or auto-approved) is logged to `audit_trail` with: `agent`, `tool_name`, `action_category`, `authority_decision`, `executed bool`, `execution_time_ms`, full `input_data` + `output_data` jsonb. Complete tamper-evident record of everything Chief has done.

### Input/Output Guardrails

`guardrails.py` checks every message pre- and post-agent:
- Input: blocks prompt injection patterns (`ignore previous instructions`, `pretend you are`, `reveal system prompt`), blocks domain violations (asking Pulse for financial advice)
- Output: detects PII leakage, sanitizes before returning to user
- Quality scoring (0-100): responses below threshold flagged and logged to `agent_quality_log`

### Credential Storage

OAuth tokens (Gmail, GitHub, WHOOP) stored in `connector_tokens` table with RLS. Tokens are refreshed automatically on expiry. AWS credentials in server-only `.env` files, never committed (`.gitignore`).

---

## 15. Repository and Dev Info

**Repo**: `MSherbinii/ChiefAI` (GitHub)
**Supabase project**: `hjuanwztmwbwjzoquxtl` (Chief — separate from Lumina `vjqamdrmynwkrpichhzc`)
**Dev auth**: `sherbini2002@gmail.com` / `Chief2026!`
**Redirect URLs**: `http://localhost:3000/callback`, `http://localhost:3002/callback`

### Start Commands
```bash
# Terminal 1: Next.js
cd apps/web && npm run dev
# → http://localhost:3002

# Terminal 2: FastAPI
cd services/agents && .venv/Scripts/python.exe -m uvicorn main:app --reload --port 8001
# → http://localhost:8001

# Tests
cd services/agents && .venv/Scripts/python.exe -m pytest tests/ -v

# Live eval (real Bedrock calls)
cd services/agents && .venv/Scripts/python.exe -m eval.runner
```

### Key Python Modules
| Module | Role |
|--------|------|
| `orchestrator.py` | Routes messages to agents, guardrails, quality scoring, memory |
| `agents.py` | 7 agent classes with domain configs and handle() method |
| `guardrails.py` | Input/output guardrails, response quality scoring (0-100) |
| `memory.py` | Saves interactions to chat_messages, loads conversation history |
| `feedback.py` | RL feedback from approval/rejection, auto-approve learning |
| `proactive.py` | Background scanner: health anomalies, stale comms, velocity drops |
| `hierarchy.py` | AGENT_HIERARCHY dict, delegation, commitments, agent messages |
| `semantic_search.py` | pgvector semantic search over Life Graph |
| `embeddings.py` | Titan/sentence-transformers embeddings for entities/comms |
| `voice_intent.py` | Classifies voice/text input → agent routing |
| `knowledge_extractor.py` | Extracts entities/relationships from emails + commits |
| `document_extractor.py` | Claude Vision OCR for uploaded documents |
| `pydantic_agents.py` | PydanticAI structured outputs factory |
| `llm.py` | Bedrock/Anthropic client factory + model IDs |
| `brief/generator.py` | Morning Brief generation (Sonnet) |
| `scoring/momentum.py` | Momentum Score calculation (multi-domain) |
| `email_intelligence/` | Deep scan, clusterer, case discoverer, cross-entity reasoner, pattern scanner, agentic pipeline |
| `connectors/gmail.py` | Gmail OAuth + full inbox pagination |
| `connectors/github.py` | GitHub API sync |
| `connectors/whoop.py` | WHOOP OAuth sync |
| `connectors/google_calendar.py` | Google Calendar sync → commitments |
| `tools/` | Real tool implementations: health, comms, project, finance, admin |
| `eval/runner.py` | Live LLM evaluation suite with quality scoring |

---

*Last updated: May 2026 | 137 tests passing | 52,459 emails | 87 cases | 7 agents*
