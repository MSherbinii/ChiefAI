alter table public.briefs
  add column if not exists best_move text,
  add column if not exists patterns text[] default '{}';
