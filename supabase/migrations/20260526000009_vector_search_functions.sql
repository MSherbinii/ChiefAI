-- Vector search functions for Life Graph semantic search (pgvector)

-- Semantic search function for entities
create or replace function public.search_entities(
  query_embedding vector(1536),
  user_id_filter uuid,
  match_count int default 5
)
returns table (
  id uuid,
  name text,
  type text,
  properties jsonb,
  similarity float
)
language sql stable
as $$
  select
    id, name, type, properties,
    1 - (embedding <=> query_embedding) as similarity
  from public.entities
  where user_id = user_id_filter
    and embedding is not null
  order by embedding <=> query_embedding
  limit match_count;
$$;

-- Semantic search function for communications
create or replace function public.search_communications(
  query_embedding vector(1536),
  user_id_filter uuid,
  match_count int default 5
)
returns table (
  id uuid,
  thread_id text,
  subject text,
  participants text[],
  last_message_at timestamptz,
  staleness_days integer,
  similarity float
)
language sql stable
as $$
  select
    id, thread_id, subject, participants, last_message_at, staleness_days,
    1 - (embedding <=> query_embedding) as similarity
  from public.lg_communications
  where user_id = user_id_filter
    and embedding is not null
  order by embedding <=> query_embedding
  limit match_count;
$$;
