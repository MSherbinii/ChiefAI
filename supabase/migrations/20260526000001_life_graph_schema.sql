-- Enable pgvector for semantic search
create extension if not exists vector;

-- ─── Users (extends Supabase auth.users) ───────────────────────────────────
create table public.profiles (
  id          uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  timezone    text default 'Europe/Berlin',
  created_at  timestamptz default now()
);
alter table public.profiles enable row level security;
create policy "Users see own profile"
  on public.profiles for all
  using (auth.uid() = id);

-- ─── Life Graph: People ────────────────────────────────────────────────────
create table public.lg_people (
  id               uuid primary key default gen_random_uuid(),
  user_id          uuid not null references public.profiles(id) on delete cascade,
  name             text not null,
  relationship     text,
  context          text,
  last_interaction timestamptz,
  importance       smallint default 3 check (importance between 1 and 5),
  embedding        vector(1536),
  created_at       timestamptz default now(),
  updated_at       timestamptz default now()
);
alter table public.lg_people enable row level security;
create policy "Users own their people"
  on public.lg_people for all
  using (auth.uid() = user_id);

-- ─── Life Graph: Projects ─────────────────────────────────────────────────
create table public.lg_projects (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references public.profiles(id) on delete cascade,
  name        text not null,
  type        text,
  status      text default 'active',
  deadline    date,
  tools       text[],
  embedding   vector(1536),
  created_at  timestamptz default now(),
  updated_at  timestamptz default now(),
  unique(user_id, name)
);
alter table public.lg_projects enable row level security;
create policy "Users own their projects"
  on public.lg_projects for all
  using (auth.uid() = user_id);

-- ─── Life Graph: Health entries ───────────────────────────────────────────
create table public.lg_health (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references public.profiles(id) on delete cascade,
  metric      text not null,
  value       jsonb not null,
  source      text,
  confidence  text default 'high',
  recorded_at timestamptz not null,
  created_at  timestamptz default now(),
  unique(user_id, metric, recorded_at)
);
alter table public.lg_health enable row level security;
create policy "Users own their health"
  on public.lg_health for all
  using (auth.uid() = user_id);

-- ─── Life Graph: Finance entries ──────────────────────────────────────────
create table public.lg_finance (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.profiles(id) on delete cascade,
  account         text,
  type            text not null,
  amount_cents    bigint,
  currency        text default 'EUR',
  description     text,
  category        text,
  is_subscription boolean default false,
  recurring_period text,
  last_used_at    timestamptz,
  transaction_at  timestamptz,
  created_at      timestamptz default now()
);
alter table public.lg_finance enable row level security;
create policy "Users own their finance"
  on public.lg_finance for all
  using (auth.uid() = user_id);

-- ─── Life Graph: Communications ───────────────────────────────────────────
create table public.lg_communications (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.profiles(id) on delete cascade,
  thread_id       text,
  channel         text not null,
  participants    text[],
  subject         text,
  summary         text,
  last_message_at timestamptz,
  status          text default 'active',
  staleness_days  integer default 0,
  urgency         text default 'normal',
  related_person_id uuid references public.lg_people(id),
  related_project_id uuid references public.lg_projects(id),
  embedding       vector(1536),
  created_at      timestamptz default now(),
  updated_at      timestamptz default now(),
  unique(user_id, thread_id)
);
alter table public.lg_communications enable row level security;
create policy "Users own their communications"
  on public.lg_communications for all
  using (auth.uid() = user_id);

-- ─── Life Graph: Documents ────────────────────────────────────────────────
create table public.lg_documents (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.profiles(id) on delete cascade,
  type            text not null,
  title           text,
  extracted_fields jsonb,
  source          text,
  storage_path    text,
  expires_at      date,
  embedding       vector(1536),
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);
alter table public.lg_documents enable row level security;
create policy "Users own their documents"
  on public.lg_documents for all
  using (auth.uid() = user_id);

-- ─── Life Graph: Goals ────────────────────────────────────────────────────
create table public.lg_goals (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references public.profiles(id) on delete cascade,
  domain      text not null,
  title       text not null,
  target      text,
  progress    smallint default 0 check (progress between 0 and 100),
  deadline    date,
  blockers    text[],
  status      text default 'active',
  created_at  timestamptz default now(),
  updated_at  timestamptz default now()
);
alter table public.lg_goals enable row level security;
create policy "Users own their goals"
  on public.lg_goals for all
  using (auth.uid() = user_id);

-- ─── Approval Queue ───────────────────────────────────────────────────────
create table public.approval_queue (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references public.profiles(id) on delete cascade,
  agent        text not null,
  action_type  text not null,
  risk_level   text default 'approve',
  title        text not null,
  description  text,
  payload      jsonb,
  context_capsule jsonb,
  status       text default 'pending',
  created_at   timestamptz default now(),
  expires_at   timestamptz default (now() + interval '24 hours')
);
alter table public.approval_queue enable row level security;
create policy "Users own their queue"
  on public.approval_queue for all
  using (auth.uid() = user_id);

-- ─── Chat Messages ────────────────────────────────────────────────────────
create table public.chat_messages (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references public.profiles(id) on delete cascade,
  role        text not null check (role in ('user', 'assistant')),
  content     text not null,
  agent       text,
  metadata    jsonb,
  created_at  timestamptz default now()
);
alter table public.chat_messages enable row level security;
create policy "Users own their messages"
  on public.chat_messages for all
  using (auth.uid() = user_id);

-- ─── Momentum Score snapshots ─────────────────────────────────────────────
create table public.momentum_scores (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references public.profiles(id) on delete cascade,
  total        smallint not null check (total between 0 and 100),
  body         smallint check (body between 0 and 100),
  money        smallint check (money between 0 and 100),
  work         smallint check (work between 0 and 100),
  admin        smallint check (admin between 0 and 100),
  discipline   smallint check (discipline between 0 and 100),
  scored_at    timestamptz default now()
);
alter table public.momentum_scores enable row level security;
create policy "Users own their scores"
  on public.momentum_scores for all
  using (auth.uid() = user_id);

-- ─── Indexes ──────────────────────────────────────────────────────────────
create index lg_health_user_metric on public.lg_health(user_id, metric, recorded_at desc);
create index lg_finance_user_type on public.lg_finance(user_id, type, transaction_at desc);
create index lg_comms_user_status on public.lg_communications(user_id, status, last_message_at desc);
create index chat_messages_user_created on public.chat_messages(user_id, created_at desc);
create index approval_queue_user_status on public.approval_queue(user_id, status, created_at desc);
