create table if not exists public.agent_quality_log (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.profiles(id) on delete cascade,
  agent           text not null,
  message_hash    bigint not null,
  quality_score   real not null,
  issues          text[] default '{}',
  logged_at       timestamptz default now(),
  unique(user_id, agent, message_hash)
);
alter table public.agent_quality_log enable row level security;
create policy "Users own their quality log"
  on public.agent_quality_log for all
  using (auth.uid() = user_id);
create index agent_quality_user_agent on public.agent_quality_log(user_id, agent, logged_at desc);
