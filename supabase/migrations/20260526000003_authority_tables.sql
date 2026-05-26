-- Audit trail: every agent tool call logged regardless of outcome
create table public.audit_trail (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid not null references public.profiles(id) on delete cascade,
  agent          text not null,
  tool_name      text not null,
  action_category text not null,
  authority_decision text not null,
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
