-- Add staleness_days as a plain integer column (computed at write time via trigger)
alter table public.lg_communications
  add column if not exists staleness_days integer default 0;

-- Update existing rows
update public.lg_communications
  set staleness_days = extract(day from now() - last_message_at)::integer
  where last_message_at is not null;

-- Function to auto-update staleness_days on insert/update
create or replace function public.update_staleness_days()
returns trigger
language plpgsql
security definer
as $$
begin
  if new.last_message_at is not null then
    new.staleness_days := extract(day from now() - new.last_message_at)::integer;
  else
    new.staleness_days := 0;
  end if;
  return new;
end;
$$;

-- Trigger on lg_communications insert/update
drop trigger if exists trg_update_staleness on public.lg_communications;
create trigger trg_update_staleness
  before insert or update of last_message_at
  on public.lg_communications
  for each row execute function public.update_staleness_days();
