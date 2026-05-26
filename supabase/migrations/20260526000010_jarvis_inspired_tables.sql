-- Inspired by Jarvis vault/schema.ts commitments, agent_messages, and recent_objects tables.
-- Adapted for Chief's multi-user Supabase architecture (PostgreSQL + RLS).
--
-- Jarvis originals are single-user SQLite; these versions add:
--   • user_id FK → public.profiles (multi-tenant)
--   • Row-Level Security on every table
--   • PostgreSQL-native types (uuid, timestamptz, jsonb)
--   • Composite indexes tuned for Chief's query patterns

-- ─── commitments ────────────────────────────────────────────────────────────
-- Task lifecycle: pending → active → completed / failed / escalated.
-- Jarvis: vault/schema.ts createTables() "commitments" table.
-- Added: user_id, why, retry_count/max_retries (Jarvis has retry_policy blob).

create table if not exists public.commitments (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.profiles(id) on delete cascade,
  agent           text not null,
  what            text not null,
  why             text,
  when_due        timestamptz,
  priority        text default 'normal'
    check (priority in ('low', 'normal', 'high', 'critical')),
  status          text default 'pending'
    check (status in ('pending', 'active', 'completed', 'failed', 'escalated')),
  retry_count     integer default 0,
  max_retries     integer default 3,
  context         jsonb default '{}',
  assigned_to     text,   -- which sub-agent owns this commitment
  created_from    text,   -- which parent agent delegated it (mirrors delegation.ts)
  result          text,   -- outcome summary on completion/failure
  sort_order      integer default 0,
  created_at      timestamptz default now(),
  updated_at      timestamptz default now(),
  completed_at    timestamptz
);

alter table public.commitments enable row level security;

create policy "Users own their commitments"
  on public.commitments for all
  using (auth.uid() = user_id);

-- Composite index: list active/pending by priority (most common query pattern)
create index if not exists commitments_user_status_priority
  on public.commitments(user_id, status, priority desc);

-- For due-date scheduling queries
create index if not exists commitments_user_due
  on public.commitments(user_id, when_due)
  where when_due is not null;

-- ─── agent_messages ──────────────────────────────────────────────────────────
-- Inter-agent communication: parent → child delegation and child → parent reports.
-- Jarvis: vault/schema.ts "agent_messages" table + delegation.ts sendMessage().
-- Added: user_id, responded flag (Jarvis uses deadline only for response tracking).

create table if not exists public.agent_messages (
  id                uuid primary key default gen_random_uuid(),
  user_id           uuid not null references public.profiles(id) on delete cascade,
  from_agent        text not null,
  to_agent          text not null,
  type              text not null
    check (type in ('task', 'report', 'question', 'escalation')),
  content           text not null,
  priority          text default 'normal'
    check (priority in ('low', 'normal', 'high', 'urgent')),
  requires_response boolean default false,
  responded         boolean default false,
  commitment_id     uuid references public.commitments(id) on delete set null,
  created_at        timestamptz default now()
);

alter table public.agent_messages enable row level security;

create policy "Users own their agent messages"
  on public.agent_messages for all
  using (auth.uid() = user_id);

-- Primary read pattern: "unread messages for agent X"
create index if not exists agent_messages_to_agent_pending
  on public.agent_messages(user_id, to_agent, responded)
  where responded = false;

-- For reading full conversation thread between two agents
create index if not exists agent_messages_thread
  on public.agent_messages(user_id, from_agent, to_agent, created_at desc);

-- ─── recent_objects ──────────────────────────────────────────────────────────
-- Bounded LRU access log — max 50 rows per user enforced by trigger below.
-- Jarvis: vault/schema.ts "recent_objects" (single-user, capped externally at 50).
-- The UNIQUE constraint on (user_id, object_type, object_id) means re-accessing
-- the same object bumps accessed_at rather than duplicating the row.

create table if not exists public.recent_objects (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references public.profiles(id) on delete cascade,
  object_type   text not null,  -- 'profile','thread','project','document','goal','commitment'
  object_id     text not null,
  label         text,           -- human-readable name for display
  meta          jsonb default '{}',
  accessed_at   timestamptz default now(),
  unique(user_id, object_type, object_id)
);

alter table public.recent_objects enable row level security;

create policy "Users own their recent objects"
  on public.recent_objects for all
  using (auth.uid() = user_id);

-- Primary read: most-recently accessed first
create index if not exists recent_objects_user_accessed
  on public.recent_objects(user_id, accessed_at desc);

-- ─── Trigger: cap recent_objects at 50 per user ──────────────────────────────
-- Jarvis caps this externally in the API layer; here we enforce it in the DB.

create or replace function public.trim_recent_objects()
returns trigger language plpgsql as $$
begin
  delete from public.recent_objects
  where user_id = NEW.user_id
    and id not in (
      select id from public.recent_objects
      where user_id = NEW.user_id
      order by accessed_at desc
      limit 50
    );
  return NEW;
end;
$$;

drop trigger if exists trg_trim_recent_objects on public.recent_objects;
create trigger trg_trim_recent_objects
  after insert on public.recent_objects
  for each row execute function public.trim_recent_objects();

-- ─── updated_at auto-update for commitments ──────────────────────────────────
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  NEW.updated_at = now();
  return NEW;
end;
$$;

drop trigger if exists trg_commitments_updated_at on public.commitments;
create trigger trg_commitments_updated_at
  before update on public.commitments
  for each row execute function public.set_updated_at();
