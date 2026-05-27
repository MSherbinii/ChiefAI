-- Email Intelligence Engine v2 tables

-- email_raw: complete inbox store
create table public.email_raw (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.profiles(id) on delete cascade,
  gmail_id        text not null,
  thread_id       text not null,
  from_email      text not null,
  from_name       text,
  to_emails       text[] default '{}',
  subject         text,
  snippet         text,
  body_text       text,
  date            timestamptz not null,
  labels          text[] default '{}',
  is_sent         boolean default false,
  is_read         boolean default true,
  has_attachments boolean default false,
  in_reply_to     text,
  embedding       vector(1536),
  processed       boolean default false,
  created_at      timestamptz default now(),
  unique(user_id, gmail_id)
);
alter table public.email_raw enable row level security;
create policy "Users own their raw emails"
  on public.email_raw for all using (auth.uid() = user_id);
create index email_raw_user_date on public.email_raw(user_id, date desc);
create index email_raw_user_thread on public.email_raw(user_id, thread_id);
create index email_raw_user_from on public.email_raw(user_id, from_email);
create index email_raw_unprocessed on public.email_raw(user_id, processed) where processed = false;

-- email_cases: ongoing situations
create table public.email_cases (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.profiles(id) on delete cascade,
  title           text not null,
  status          text default 'open' check (status in ('open','progressing','stalled','needs_action','resolved')),
  priority        text default 'normal' check (priority in ('low','normal','high','critical')),
  category        text,
  summary         text,
  entities        uuid[] default '{}',
  email_ids       uuid[] default '{}',
  thread_ids      text[] default '{}',
  pending_action  text,
  stalled_since   timestamptz,
  user_notes      text,
  timeline        jsonb default '[]',
  confidence      real default 0.7,
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);
alter table public.email_cases enable row level security;
create policy "Users own their cases"
  on public.email_cases for all using (auth.uid() = user_id);
create index email_cases_user_status on public.email_cases(user_id, status, priority desc);

-- email_subscriptions: newsletter/recurring detection
create table public.email_subscriptions (
  id                   uuid primary key default gen_random_uuid(),
  user_id              uuid not null references public.profiles(id) on delete cascade,
  entity_id            uuid references public.entities(id),
  sender_email         text not null,
  sender_name          text,
  frequency            text,
  avg_interval_days    real,
  total_received       integer default 0,
  last_received        timestamptz,
  opened_count         integer default 0,
  replied_count        integer default 0,
  engagement_score     real default 0,
  has_unsubscribe_link boolean default false,
  unsubscribe_url      text,
  status               text default 'active' check (status in ('active','unsubscribed','paused')),
  user_decision        text check (user_decision in ('keep','unsubscribe','undecided')),
  created_at           timestamptz default now(),
  unique(user_id, sender_email)
);
alter table public.email_subscriptions enable row level security;
create policy "Users own their subscriptions"
  on public.email_subscriptions for all using (auth.uid() = user_id);

-- email_feedback: RL training signal
create table public.email_feedback (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references public.profiles(id) on delete cascade,
  feedback_type text not null check (feedback_type in ('case_confirm','case_reject','case_merge','entity_correct','priority_change','action_approve','action_reject')),
  target_id     uuid,
  target_type   text check (target_type in ('case','entity','subscription')),
  old_value     jsonb,
  new_value     jsonb,
  context       text,
  created_at    timestamptz default now()
);
alter table public.email_feedback enable row level security;
create policy "Users own their feedback"
  on public.email_feedback for all using (auth.uid() = user_id);

-- upgrade entities table for email intelligence
alter table public.entities add column if not exists
  relationship_type text check (relationship_type in (
    'service_provider','bank','debt_collector','employer','professor',
    'newsletter','marketplace','government','friend','unknown'
  ));
alter table public.entities add column if not exists email_domains text[] default '{}';
alter table public.entities add column if not exists first_contact timestamptz;
alter table public.entities add column if not exists last_contact timestamptz;
alter table public.entities add column if not exists interaction_count integer default 0;
alter table public.entities add column if not exists engagement_score real default 0;

-- scan progress tracking
create table public.email_scan_status (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.profiles(id) on delete cascade unique,
  status          text default 'idle' check (status in ('idle','scanning','clustering','detecting_subscriptions','complete','error')),
  total_emails    integer default 0,
  scanned_emails  integer default 0,
  error_message   text,
  started_at      timestamptz,
  completed_at    timestamptz,
  updated_at      timestamptz default now()
);
alter table public.email_scan_status enable row level security;
create policy "Users own their scan status"
  on public.email_scan_status for all using (auth.uid() = user_id);
