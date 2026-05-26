-- Knowledge graph: entities
create table public.entities (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references public.profiles(id) on delete cascade,
  type        text not null,
  name        text not null,
  properties  jsonb default '{}',
  source      text,
  embedding   vector(1536),
  created_at  timestamptz default now(),
  updated_at  timestamptz default now(),
  unique(user_id, type, name)
);
alter table public.entities enable row level security;
create policy "Users own their entities"
  on public.entities for all using (auth.uid() = user_id);

-- Facts: subject -> predicate -> object with confidence
create table public.facts (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references public.profiles(id) on delete cascade,
  subject_id   uuid not null references public.entities(id) on delete cascade,
  predicate    text not null,
  object       text not null,
  object_id    uuid references public.entities(id),
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
  type         text not null,
  properties   jsonb default '{}',
  created_at   timestamptz default now(),
  unique(user_id, from_id, to_id, type)
);
alter table public.relationships enable row level security;
create policy "Users own their relationships"
  on public.relationships for all using (auth.uid() = user_id);
create index relationships_from on public.relationships(user_id, from_id);
create index relationships_to on public.relationships(user_id, to_id);
