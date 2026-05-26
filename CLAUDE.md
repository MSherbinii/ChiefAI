# Chief — Personal Life Operating System

## What is Chief?

Chief is a personal life OS that connects health (WHOOP), finances (banks), work (GitHub), communication (Gmail), documents, and admin into one AI intelligence layer. It generates a daily Morning Brief, calculates a Momentum Score, and routes requests to specialized sub-agents.

## Monorepo Structure

```
chief/
├── apps/web/          # Next.js 15 App Router frontend
├── services/agents/   # Python FastAPI agent service
└── supabase/migrations/ # DB schema (auto-applied via GitHub integration)
```

## Running the Project

```bash
# Terminal 1: Next.js (port 3002 if 3000 is taken)
cd apps/web && npm run dev

# Terminal 2: Python agents
cd services/agents && .venv/Scripts/python.exe -m uvicorn main:app --reload --port 8001
```

## Environment Variables

**apps/web/.env.local:**
```
NEXT_PUBLIC_SUPABASE_URL=https://hjuanwztmwbwjzoquxtl.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_ESMyOuZQfhhr71QyE1a8bA_BHiBi0e0
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
AGENT_SERVICE_URL=http://localhost:8001
GOOGLE_CLIENT_ID=... (from Google Cloud Console)
GOOGLE_CLIENT_SECRET=...
WHOOP_CLIENT_ID=... (from developer.whoop.com)
WHOOP_CLIENT_SECRET=...
```

**services/agents/.env:**
```
SUPABASE_URL=https://hjuanwztmwbwjzoquxtl.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
AWS_ACCESS_KEY_ID=...  (for Amazon Bedrock)
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=eu-central-1
```

## Architecture

- **LLM**: Amazon Bedrock (eu-central-1) via `anthropic.AnthropicBedrock()`
  - Routing: `eu.anthropic.claude-haiku-4-5-20251001-v1:0`
  - Agents: `eu.anthropic.claude-haiku-4-5-20251001-v1:0`
  - Brief/Vision: `eu.anthropic.claude-sonnet-4-6-20251231-v1:0`
- **Database**: Supabase (Postgres + pgvector) — project `hjuanwztmwbwjzoquxtl`
- **Embeddings**: Amazon Titan Embeddings v2 (1024 dims, padded to 1536 for pgvector)
- **Auth**: Supabase magic link + email/password

## The 7 Agents

| Agent | Domain | Key tools |
|-------|--------|-----------|
| Chief | Orchestrator | Cross-domain synthesis, delegation |
| Pulse | Health | WHOOP recovery, sleep, workouts, nutrition |
| Echo | Communication | Gmail threads, email drafts, staleness |
| Forge | Projects | GitHub commits, velocity, deadlines, calendar |
| Ledger | Finance | Spending, subscriptions, affordability |
| Clerk | Admin | Documents, insurance, German bureaucracy |
| Scout | Research | Comparisons, courses, regulations |

## Key Python Modules

- `orchestrator.py` — routes messages to agents, guardrails, quality scoring, memory
- `guardrails.py` — input/output guardrails, response quality scoring (0-100)
- `memory.py` — saves interactions to chat_messages, loads conversation history
- `feedback.py` — RL feedback from approval/rejection, auto-approve learning
- `proactive.py` — background scanner: health anomalies, stale comms, velocity drops
- `hierarchy.py` — agent hierarchy, delegation, commitments, agent messages
- `semantic_search.py` — pgvector semantic search over Life Graph
- `embeddings.py` — Titan/sentence-transformers embeddings for entities/comms
- `voice_intent.py` — classifies voice/text input → agent routing
- `knowledge_extractor.py` — extracts entities/relationships from emails + commits
- `document_extractor.py` — Claude Vision OCR for uploaded documents
- `pydantic_agents.py` — PydanticAI structured outputs factory
- `llm.py` — Bedrock/Anthropic client factory + model IDs
- `tools/` — real tool implementations (health, comms, project, finance, admin)

## Key Next.js Routes

- `/today` — Morning Brief + Momentum Score + Approval Queue (auto-generates if missing)
- `/chat` — Multi-agent chat with color-coded badges, slash commands (/brief /score /scan)
- `/domains` — Domain deep-dives: Health / Work / Finance / Admin tabs
- `/graph` — Life Graph browser: entities, facts, relationships
- `/replay` — Weekly Replay from goal_check_ins history
- `/settings` — Connectors, document upload, agent status, profile
- `/onboarding` — 3-step wizard: name → roles → focus goals

## Running Tests

```bash
cd services/agents

# Unit + integration tests
.venv/Scripts/python.exe -m pytest tests/ -v

# Live LLM evaluation (makes real Bedrock calls)
.venv/Scripts/python.exe -m eval.runner
```

## Supabase

- **Project**: hjuanwztmwbwjzoquxtl (Chief — separate from Lumina)
- **Migrations**: `supabase/migrations/` — auto-applied via GitHub integration on push to master
- **Key tables**: profiles, lg_health, lg_communications, lg_projects, lg_finance, lg_documents, lg_goals, entities, facts, relationships, commitments, agent_messages, approval_queue, audit_trail, approval_patterns, briefs, goal_check_ins, momentum_scores, connector_tokens, agent_quality_log

## Supabase GitHub Integration

Connected to `MSherbinii/ChiefAI` — migrations in `supabase/migrations/` are auto-applied on push.

## Auth

- Email: `sherbini2002@gmail.com` / `Chief2026!` (dev account)
- Magic link and OAuth also supported
- Supabase redirect URLs must include `http://localhost:3000/callback` and `http://localhost:3002/callback`
