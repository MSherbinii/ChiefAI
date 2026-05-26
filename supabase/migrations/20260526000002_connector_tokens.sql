-- Stores OAuth tokens and credentials for all connectors per user
create table public.connector_tokens (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid not null references public.profiles(id) on delete cascade,
  connector      text not null,
  access_token   text,
  refresh_token  text,
  token_expiry   timestamptz,
  extra          jsonb,
  last_synced_at timestamptz,
  sync_status    text default 'idle',
  error_message  text,
  created_at     timestamptz default now(),
  updated_at     timestamptz default now(),
  unique(user_id, connector)
);

alter table public.connector_tokens enable row level security;

create policy "Users own their tokens"
  on public.connector_tokens for all
  using (auth.uid() = user_id);

create index connector_tokens_user_connector
  on public.connector_tokens(user_id, connector);
