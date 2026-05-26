# Chief Phase 0 — Foundation (Real Connectors, No Stubs)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold a working monorepo with real OAuth connectors (Gmail, Google Calendar, WHOOP), GitHub PAT, and IMAP uni email. Morning Brief and Momentum Score only render once at least Gmail is connected and has synced real data. Zero stub/demo data anywhere.

**Architecture:** Monorepo — `apps/web` (Next.js 15 App Router) + `services/agents` (Python FastAPI). Next.js API routes are the gateway; browser never hits Python directly. Supabase for auth/DB/realtime. Connectors sync in background via Python jobs, writing normalized entities into the Life Graph tables. The Today view checks connection status and shows an onboarding gate if no sources are live.

**Tech Stack:** Next.js 15, Supabase JS v2, Python 3.11+ / FastAPI, Google OAuth 2.0, WHOOP OAuth 2.0, GitHub REST API, imaplib (IMAP), Tailwind CSS v3, Framer Motion 12, Radix UI, Zod v4, Zustand v5, React 19, TypeScript 5, Anthropic SDK.

---

## Updated File Map (additions over base plan)

```
chief/
├── apps/web/
│   ├── app/
│   │   ├── (app)/
│   │   │   ├── today/page.tsx          ← gates on connector status, no stubs
│   │   │   └── settings/page.tsx       ← real OAuth connect buttons + sync status
│   │   └── api/
│   │       ├── chat/route.ts           ← gateway to Python
│   │       └── connectors/
│   │           ├── google/
│   │           │   ├── auth/route.ts   ← initiates Google OAuth flow
│   │           │   └── callback/route.ts ← handles Google OAuth callback, stores tokens
│   │           └── whoop/
│   │               ├── auth/route.ts   ← initiates WHOOP OAuth flow
│   │               └── callback/route.ts ← handles WHOOP callback, stores tokens
│   ├── components/
│   │   ├── today/
│   │   │   ├── ConnectGate.tsx         ← shown when no connector is live
│   │   │   ├── MorningBrief.tsx        ← built from real DB data, no props stub
│   │   │   ├── MomentumScore.tsx       ← reads real momentum_scores row
│   │   │   └── ApprovalQueue.tsx       ← reads real approval_queue rows
│   │   └── settings/
│   │       └── ConnectorCard.tsx       ← real status, real connect/disconnect buttons
│   └── lib/
│       └── connectors.ts               ← queries connector_tokens table for status
├── services/agents/
│   ├── connectors/
│   │   ├── gmail.py                    ← Gmail OAuth token refresh + message sync
│   │   ├── google_calendar.py          ← Calendar event sync
│   │   ├── github.py                   ← GitHub PAT repo/commit sync
│   │   ├── whoop.py                    ← WHOOP OAuth token refresh + data sync
│   │   └── imap_email.py               ← IMAP sync for uni email
│   ├── sync_runner.py                  ← orchestrates all connector syncs on schedule
│   └── brief_generator.py             ← generates Morning Brief from real Life Graph data
└── supabase/migrations/
    └── 0002_connector_tokens.sql       ← stores OAuth tokens per user per connector
```

---

## Task 1: Base monorepo scaffold (from original plan, unchanged)

Run Tasks 1–6 from `2026-05-26-chief-phase0-foundation.md` first (rename dir, Next.js scaffold, design system port, Supabase schema, auth wiring, app shell). Those tasks are unchanged. Come back here for Task 2 onwards.

---

## Task 2: Connector tokens schema

**Files:**
- Create: `supabase/migrations/0002_connector_tokens.sql`

- [ ] **Step 1: Write migration**

```sql
-- supabase/migrations/0002_connector_tokens.sql
create table public.connector_tokens (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid not null references public.profiles(id) on delete cascade,
  connector      text not null,        -- 'gmail', 'google_calendar', 'github', 'whoop', 'imap_uni'
  access_token   text,                 -- encrypted at application layer before storage
  refresh_token  text,
  token_expiry   timestamptz,
  extra          jsonb,                -- e.g. { email: 'user@uni.edu', imap_host: 'imap.uni.de' }
  last_synced_at timestamptz,
  sync_status    text default 'idle',  -- 'idle', 'syncing', 'error', 'ok'
  error_message  text,
  created_at     timestamptz default now(),
  updated_at     timestamptz default now(),
  unique(user_id, connector)
);
alter table public.connector_tokens enable row level security;
create policy "Users own their tokens"
  on public.connector_tokens for all
  using (auth.uid() = user_id);
```

- [ ] **Step 2: Apply in Supabase SQL editor**

Paste into the Supabase dashboard → SQL editor → Run. Confirm the `connector_tokens` table appears in Table Editor.

- [ ] **Step 3: Commit**

```bash
cd C:/Users/Micha/chief
git add supabase/
git commit -m "feat: add connector_tokens schema"
```

---

## Task 3: Google Cloud project + OAuth credentials

This is a manual setup task — no code, just configuration.

- [ ] **Step 1: Create Google Cloud project**

1. Go to https://console.cloud.google.com
2. Create new project named `chief-app`
3. Enable these APIs (APIs & Services → Enable APIs):
   - Gmail API
   - Google Calendar API
   - People API (for contact info)

- [ ] **Step 2: Create OAuth 2.0 credentials**

1. APIs & Services → Credentials → Create Credentials → OAuth client ID
2. Application type: **Web application**
3. Name: `Chief Local Dev`
4. Authorized redirect URIs: `http://localhost:3000/api/connectors/google/callback`
5. Save — copy **Client ID** and **Client Secret**

- [ ] **Step 3: Configure OAuth consent screen**

1. APIs & Services → OAuth consent screen
2. User type: External (for testing)
3. App name: `Chief`, support email: your email
4. Scopes: add `gmail.readonly`, `calendar.readonly`, `contacts.readonly`
5. Test users: add your personal Gmail and your uni Gmail account

- [ ] **Step 4: Add credentials to .env.local**

```bash
# Append to apps/web/.env.local
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:3000/api/connectors/google/callback
```

---

## Task 4: Google OAuth flow in Next.js

**Files:**
- Create: `apps/web/app/api/connectors/google/auth/route.ts`
- Create: `apps/web/app/api/connectors/google/callback/route.ts`

- [ ] **Step 1: Create Google OAuth initiation route**

```ts
// apps/web/app/api/connectors/google/auth/route.ts
import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const scopes = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/contacts.readonly',
    'email',
    'profile',
  ];

  const params = new URLSearchParams({
    client_id: process.env.GOOGLE_CLIENT_ID!,
    redirect_uri: process.env.GOOGLE_REDIRECT_URI!,
    response_type: 'code',
    scope: scopes.join(' '),
    access_type: 'offline',
    prompt: 'consent',
    state: searchParams.get('state') ?? 'gmail',
  });

  return NextResponse.redirect(
    `https://accounts.google.com/o/oauth2/v2/auth?${params}`
  );
}
```

- [ ] **Step 2: Create Google OAuth callback route**

```ts
// apps/web/app/api/connectors/google/callback/route.ts
import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get('code');
  const error = searchParams.get('error');

  if (error || !code) {
    return NextResponse.redirect(`${origin}/settings?error=google_auth_failed`);
  }

  // Exchange code for tokens
  const tokenRes = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      code,
      client_id: process.env.GOOGLE_CLIENT_ID!,
      client_secret: process.env.GOOGLE_CLIENT_SECRET!,
      redirect_uri: process.env.GOOGLE_REDIRECT_URI!,
      grant_type: 'authorization_code',
    }),
  });

  const tokens = await tokenRes.json();
  if (!tokenRes.ok) {
    return NextResponse.redirect(`${origin}/settings?error=token_exchange_failed`);
  }

  // Get user email from Google
  const userInfoRes = await fetch('https://www.googleapis.com/oauth2/v2/userinfo', {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
  });
  const userInfo = await userInfoRes.json();

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.redirect(`${origin}/login`);

  const expiry = new Date(Date.now() + tokens.expires_in * 1000).toISOString();

  // Upsert gmail token
  await supabase.from('connector_tokens').upsert({
    user_id: user.id,
    connector: 'gmail',
    access_token: tokens.access_token,
    refresh_token: tokens.refresh_token,
    token_expiry: expiry,
    extra: { email: userInfo.email },
    sync_status: 'idle',
    updated_at: new Date().toISOString(),
  }, { onConflict: 'user_id,connector' });

  // Also upsert calendar token (same credentials)
  await supabase.from('connector_tokens').upsert({
    user_id: user.id,
    connector: 'google_calendar',
    access_token: tokens.access_token,
    refresh_token: tokens.refresh_token,
    token_expiry: expiry,
    extra: { email: userInfo.email },
    sync_status: 'idle',
    updated_at: new Date().toISOString(),
  }, { onConflict: 'user_id,connector' });

  // Trigger initial sync via agent service
  const agentUrl = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8001';
  fetch(`${agentUrl}/sync/google`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: user.id }),
  }).catch(() => {}); // fire-and-forget

  return NextResponse.redirect(`${origin}/settings?connected=google`);
}
```

- [ ] **Step 3: Commit**

```bash
cd C:/Users/Micha/chief
git add apps/web/app/api/connectors/
git commit -m "feat: add Google OAuth connect flow (Gmail + Calendar)"
```

---

## Task 5: WHOOP developer setup + OAuth flow

- [ ] **Step 1: Register WHOOP developer app**

1. Go to https://developer.whoop.com
2. Sign in with your WHOOP account
3. Create a new app named `Chief`
4. Set redirect URI: `http://localhost:3000/api/connectors/whoop/callback`
5. Copy **Client ID** and **Client Secret**

- [ ] **Step 2: Add WHOOP credentials to .env.local**

```bash
# Append to apps/web/.env.local
WHOOP_CLIENT_ID=your-whoop-client-id
WHOOP_CLIENT_SECRET=your-whoop-client-secret
WHOOP_REDIRECT_URI=http://localhost:3000/api/connectors/whoop/callback
```

- [ ] **Step 3: Create WHOOP OAuth initiation route**

```ts
// apps/web/app/api/connectors/whoop/auth/route.ts
import { NextResponse } from 'next/server';

export async function GET() {
  const params = new URLSearchParams({
    client_id: process.env.WHOOP_CLIENT_ID!,
    redirect_uri: process.env.WHOOP_REDIRECT_URI!,
    response_type: 'code',
    scope: 'read:recovery read:sleep read:workout read:body_measurement read:cycles offline',
  });

  return NextResponse.redirect(
    `https://api.prod.whoop.com/oauth/oauth2/auth?${params}`
  );
}
```

- [ ] **Step 4: Create WHOOP callback route**

```ts
// apps/web/app/api/connectors/whoop/callback/route.ts
import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get('code');
  const error = searchParams.get('error');

  if (error || !code) {
    return NextResponse.redirect(`${origin}/settings?error=whoop_auth_failed`);
  }

  const tokenRes = await fetch('https://api.prod.whoop.com/oauth/oauth2/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      code,
      client_id: process.env.WHOOP_CLIENT_ID!,
      client_secret: process.env.WHOOP_CLIENT_SECRET!,
      redirect_uri: process.env.WHOOP_REDIRECT_URI!,
      grant_type: 'authorization_code',
    }),
  });

  const tokens = await tokenRes.json();
  if (!tokenRes.ok) {
    return NextResponse.redirect(`${origin}/settings?error=whoop_token_failed`);
  }

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.redirect(`${origin}/login`);

  const expiry = new Date(Date.now() + tokens.expires_in * 1000).toISOString();

  await supabase.from('connector_tokens').upsert({
    user_id: user.id,
    connector: 'whoop',
    access_token: tokens.access_token,
    refresh_token: tokens.refresh_token,
    token_expiry: expiry,
    sync_status: 'idle',
    updated_at: new Date().toISOString(),
  }, { onConflict: 'user_id,connector' });

  const agentUrl = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8001';
  fetch(`${agentUrl}/sync/whoop`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: user.id }),
  }).catch(() => {});

  return NextResponse.redirect(`${origin}/settings?connected=whoop`);
}
```

- [ ] **Step 5: Commit**

```bash
cd C:/Users/Micha/chief
git add apps/web/app/api/connectors/whoop/
git commit -m "feat: add WHOOP OAuth connect flow"
```

---

## Task 6: GitHub PAT connector

GitHub uses a Personal Access Token — no OAuth app needed.

- [ ] **Step 1: Create GitHub PAT**

1. Go to https://github.com/settings/tokens/new (classic)
2. Note: `Chief — repo activity`
3. Expiration: 90 days
4. Scopes: `repo` (read access to repos, commits, PRs)
5. Generate and copy the token

- [ ] **Step 2: Create GitHub PAT save route**

```ts
// apps/web/app/api/connectors/github/save/route.ts
import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { z } from 'zod';

const Body = z.object({ pat: z.string().min(10), username: z.string().min(1) });

export async function POST(request: Request) {
  const body = await request.json();
  const parsed = Body.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: 'Invalid PAT or username' }, { status: 400 });
  }

  // Verify PAT works
  const verifyRes = await fetch('https://api.github.com/user', {
    headers: {
      Authorization: `token ${parsed.data.pat}`,
      'User-Agent': 'chief-app',
    },
  });
  if (!verifyRes.ok) {
    return NextResponse.json({ error: 'GitHub PAT is invalid or expired' }, { status: 400 });
  }
  const ghUser = await verifyRes.json();

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  await supabase.from('connector_tokens').upsert({
    user_id: user.id,
    connector: 'github',
    access_token: parsed.data.pat,
    extra: { username: ghUser.login, avatar_url: ghUser.avatar_url },
    sync_status: 'idle',
    updated_at: new Date().toISOString(),
  }, { onConflict: 'user_id,connector' });

  // Trigger initial sync
  const agentUrl = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8001';
  fetch(`${agentUrl}/sync/github`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: user.id }),
  }).catch(() => {});

  return NextResponse.json({ ok: true, username: ghUser.login });
}
```

- [ ] **Step 3: Commit**

```bash
cd C:/Users/Micha/chief
git add apps/web/app/api/connectors/github/
git commit -m "feat: add GitHub PAT connector save + verify route"
```

---

## Task 7: IMAP uni email connector

- [ ] **Step 1: Create IMAP credentials save route**

```ts
// apps/web/app/api/connectors/imap/save/route.ts
import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { z } from 'zod';

const Body = z.object({
  email: z.string().email(),
  password: z.string().min(1),
  imap_host: z.string().min(1),
  imap_port: z.number().default(993),
});

export async function POST(request: Request) {
  const body = await request.json();
  const parsed = Body.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: 'Invalid IMAP credentials' }, { status: 400 });
  }

  // Verify credentials via agent service (Python handles actual IMAP connection)
  const agentUrl = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8001';
  const verifyRes = await fetch(`${agentUrl}/connectors/imap/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(parsed.data),
  });

  if (!verifyRes.ok) {
    const err = await verifyRes.json();
    return NextResponse.json({ error: err.detail ?? 'IMAP connection failed' }, { status: 400 });
  }

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  await supabase.from('connector_tokens').upsert({
    user_id: user.id,
    connector: 'imap_uni',
    access_token: parsed.data.password,  // stored; encrypt in prod
    extra: {
      email: parsed.data.email,
      imap_host: parsed.data.imap_host,
      imap_port: parsed.data.imap_port,
    },
    sync_status: 'idle',
    updated_at: new Date().toISOString(),
  }, { onConflict: 'user_id,connector' });

  fetch(`${agentUrl}/sync/imap_uni`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: user.id }),
  }).catch(() => {});

  return NextResponse.json({ ok: true });
}
```

- [ ] **Step 2: Commit**

```bash
cd C:/Users/Micha/chief
git add apps/web/app/api/connectors/imap/
git commit -m "feat: add IMAP uni email connector save route"
```

---

## Task 8: Settings page — real connector UI

**Files:**
- Create: `apps/web/lib/connectors.ts`
- Create: `apps/web/components/settings/ConnectorCard.tsx`
- Modify: `apps/web/app/(app)/settings/page.tsx`

- [ ] **Step 1: Create connectors lib (fetches real status)**

```ts
// apps/web/lib/connectors.ts
import { createClient } from '@/lib/supabase/server';

export type ConnectorStatus = 'connected' | 'disconnected' | 'error' | 'syncing';

export interface ConnectorState {
  connector: string;
  status: ConnectorStatus;
  lastSynced: string | null;
  extra: Record<string, string> | null;
  errorMessage: string | null;
}

export async function getConnectorStates(userId: string): Promise<Record<string, ConnectorState>> {
  const supabase = await createClient();
  const { data } = await supabase
    .from('connector_tokens')
    .select('connector, sync_status, last_synced_at, extra, error_message')
    .eq('user_id', userId);

  const result: Record<string, ConnectorState> = {};
  for (const row of data ?? []) {
    result[row.connector] = {
      connector: row.connector,
      status: row.sync_status === 'ok' ? 'connected'
             : row.sync_status === 'error' ? 'error'
             : row.sync_status === 'syncing' ? 'syncing'
             : 'disconnected',
      lastSynced: row.last_synced_at,
      extra: row.extra,
      errorMessage: row.error_message,
    };
  }
  return result;
}
```

- [ ] **Step 2: Create ConnectorCard component**

```tsx
// apps/web/components/settings/ConnectorCard.tsx
'use client';
import { useState } from 'react';
import { Panel, Button, StatusDot } from '@/components/design-system';
import type { LucideIcon } from 'lucide-react';
import type { ConnectorStatus } from '@/lib/connectors';
import { toast } from 'sonner';

interface ConnectorCardProps {
  id: string;
  name: string;
  description: string;
  icon: LucideIcon;
  status: ConnectorStatus;
  lastSynced: string | null;
  extra: Record<string, string> | null;
  errorMessage: string | null;
  connectHref?: string;           // for OAuth connectors
  onPATConnect?: (pat: string, username: string) => Promise<void>;  // for GitHub
  onIMAPConnect?: (email: string, password: string, host: string, port: number) => Promise<void>;
}

const STATUS_SEVERITY: Record<ConnectorStatus, 'ok' | 'info' | 'high' | 'med'> = {
  connected:    'ok',
  syncing:      'info',
  error:        'high',
  disconnected: 'med',
};

export function ConnectorCard({
  id, name, description, icon: Icon,
  status, lastSynced, extra, errorMessage,
  connectHref, onPATConnect, onIMAPConnect,
}: ConnectorCardProps) {
  const [showForm, setShowForm] = useState(false);
  const [patValue, setPatValue] = useState('');
  const [patUser, setPatUser] = useState('');
  const [imapEmail, setImapEmail] = useState('');
  const [imapPass, setImapPass] = useState('');
  const [imapHost, setImapHost] = useState('');
  const [imapPort, setImapPort] = useState(993);
  const [loading, setLoading] = useState(false);

  const inputCls = 'w-full h-8 px-3 rounded-[8px] bg-[rgba(247,240,255,0.04)] border border-[rgba(247,240,255,0.12)] text-[var(--v2-text)] placeholder:text-[var(--v2-subtle)] text-[13px] focus:outline-none focus:border-[var(--v2-border-focus)]';

  async function handlePATSubmit() {
    if (!onPATConnect) return;
    setLoading(true);
    try {
      await onPATConnect(patValue, patUser);
      toast.success(`GitHub connected as @${patUser}`);
      setShowForm(false);
    } catch (e: any) {
      toast.error(e.message ?? 'Failed to connect GitHub');
    } finally { setLoading(false); }
  }

  async function handleIMAPSubmit() {
    if (!onIMAPConnect) return;
    setLoading(true);
    try {
      await onIMAPConnect(imapEmail, imapPass, imapHost, imapPort);
      toast.success('Uni email connected');
      setShowForm(false);
    } catch (e: any) {
      toast.error(e.message ?? 'IMAP connection failed');
    } finally { setLoading(false); }
  }

  return (
    <Panel className="p-4 space-y-3">
      <div className="flex items-center gap-4">
        <div className="w-8 h-8 rounded-[10px] bg-[rgba(138,58,255,0.12)] border border-[rgba(138,58,255,0.20)] flex items-center justify-center flex-shrink-0">
          <Icon size={15} className="text-[var(--v2-violet)]" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-[var(--v2-text)]">{name}</span>
            {extra?.email && (
              <span className="text-[11px] text-[var(--v2-muted)]">{extra.email}</span>
            )}
            {extra?.username && (
              <span className="text-[11px] text-[var(--v2-muted)]">@{extra.username}</span>
            )}
          </div>
          <p className="text-[12px] text-[var(--v2-muted)] truncate">{description}</p>
          {errorMessage && (
            <p className="text-[11px] text-[var(--v2-crit)] mt-0.5">{errorMessage}</p>
          )}
          {lastSynced && status === 'connected' && (
            <p className="text-[10px] text-[var(--v2-subtle)] mt-0.5">
              Last synced {new Date(lastSynced).toLocaleString()}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <StatusDot severity={STATUS_SEVERITY[status]} size="xs" showLabel />
          {status === 'disconnected' || status === 'error' ? (
            connectHref ? (
              <Button variant="solid" size="xs" onClick={() => window.location.href = connectHref}>
                Connect
              </Button>
            ) : (
              <Button variant="solid" size="xs" onClick={() => setShowForm(v => !v)}>
                {showForm ? 'Cancel' : 'Connect'}
              </Button>
            )
          ) : (
            <Button variant="outline" size="xs" disabled={status === 'syncing'}>
              {status === 'syncing' ? 'Syncing…' : 'Synced'}
            </Button>
          )}
        </div>
      </div>

      {/* GitHub PAT form */}
      {showForm && onPATConnect && (
        <div className="space-y-2 pt-1">
          <input className={inputCls} placeholder="GitHub username" value={patUser} onChange={e => setPatUser(e.target.value)} />
          <input className={inputCls} placeholder="Personal Access Token (ghp_...)" type="password" value={patValue} onChange={e => setPatValue(e.target.value)} />
          <Button variant="solid" size="sm" loading={loading} onClick={handlePATSubmit}>Save PAT</Button>
        </div>
      )}

      {/* IMAP form */}
      {showForm && onIMAPConnect && (
        <div className="space-y-2 pt-1">
          <input className={inputCls} placeholder="University email address" value={imapEmail} onChange={e => setImapEmail(e.target.value)} />
          <input className={inputCls} placeholder="Password" type="password" value={imapPass} onChange={e => setImapPass(e.target.value)} />
          <input className={inputCls} placeholder="IMAP host (e.g. imap.uni-example.de)" value={imapHost} onChange={e => setImapHost(e.target.value)} />
          <input className={inputCls} placeholder="Port (default 993)" type="number" value={imapPort} onChange={e => setImapPort(Number(e.target.value))} />
          <Button variant="solid" size="sm" loading={loading} onClick={handleIMAPSubmit}>Save IMAP</Button>
        </div>
      )}
    </Panel>
  );
}
```

- [ ] **Step 3: Build real Settings page**

```tsx
// apps/web/app/(app)/settings/page.tsx
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { getConnectorStates } from '@/lib/connectors';
import { TopBar } from '@/components/layout/TopBar';
import { SettingsConnectors } from '@/components/settings/SettingsConnectors';

export default async function SettingsPage({
  searchParams,
}: {
  searchParams: Promise<{ connected?: string; error?: string }>;
}) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect('/login');

  const connectorStates = await getConnectorStates(user.id);
  const params = await searchParams;

  return (
    <>
      <TopBar title="Settings" />
      <main className="flex-1 overflow-y-auto p-4 max-w-2xl space-y-6">
        {params.connected && (
          <div className="px-4 py-2.5 rounded-[10px] bg-[rgba(56,242,168,0.08)] border border-[rgba(56,242,168,0.20)] text-[13px] text-[var(--v2-ok)]">
            ✓ {params.connected} connected successfully.
          </div>
        )}
        {params.error && (
          <div className="px-4 py-2.5 rounded-[10px] bg-[rgba(255,79,109,0.08)] border border-[rgba(255,79,109,0.20)] text-[13px] text-[var(--v2-crit)]">
            Connection failed: {params.error.replace(/_/g, ' ')}
          </div>
        )}
        <SettingsConnectors states={connectorStates} />
      </main>
    </>
  );
}
```

- [ ] **Step 4: Create SettingsConnectors client component**

```tsx
// apps/web/components/settings/SettingsConnectors.tsx
'use client';
import { Mail, Calendar, Github, Activity, BookOpen } from 'lucide-react';
import { ConnectorCard } from './ConnectorCard';
import type { ConnectorState } from '@/lib/connectors';
import { toast } from 'sonner';

interface Props {
  states: Record<string, ConnectorState>;
}

export function SettingsConnectors({ states }: Props) {
  function getState(id: string): ConnectorState {
    return states[id] ?? {
      connector: id, status: 'disconnected',
      lastSynced: null, extra: null, errorMessage: null,
    };
  }

  async function connectGitHub(pat: string, username: string) {
    const res = await fetch('/api/connectors/github/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pat, username }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    window.location.reload();
  }

  async function connectIMAP(email: string, password: string, imap_host: string, imap_port: number) {
    const res = await fetch('/api/connectors/imap/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, imap_host, imap_port }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    window.location.reload();
  }

  return (
    <section className="space-y-3">
      <div>
        <h2 className="text-sm font-semibold text-[var(--v2-text)]">Connectors</h2>
        <p className="text-[12px] text-[var(--v2-muted)] mt-0.5">
          Connect your sources. Chief builds your Life Graph from these.
        </p>
      </div>
      <div className="space-y-2">
        <ConnectorCard
          id="gmail"
          name="Gmail"
          description="Email threads, subscriptions, receipts, contacts"
          icon={Mail}
          {...getState('gmail')}
          connectHref="/api/connectors/google/auth"
        />
        <ConnectorCard
          id="google_calendar"
          name="Google Calendar"
          description="Schedule, deadlines, availability"
          icon={Calendar}
          {...getState('google_calendar')}
          connectHref="/api/connectors/google/auth"
        />
        <ConnectorCard
          id="github"
          name="GitHub"
          description="Repos, commits, activity, PRs"
          icon={Github}
          {...getState('github')}
          onPATConnect={connectGitHub}
        />
        <ConnectorCard
          id="whoop"
          name="WHOOP"
          description="Sleep, recovery, strain, HRV"
          icon={Activity}
          {...getState('whoop')}
          connectHref="/api/connectors/whoop/auth"
        />
        <ConnectorCard
          id="imap_uni"
          name="University Email"
          description="Thesis conversations, professor threads, university admin"
          icon={BookOpen}
          {...getState('imap_uni')}
          onIMAPConnect={connectIMAP}
        />
      </div>
    </section>
  );
}
```

- [ ] **Step 5: Commit**

```bash
cd C:/Users/Micha/chief
git add apps/web/
git commit -m "feat: real Settings page with live connector status and connect flows"
```

---

## Task 9: Python connector sync workers

**Files:**
- Create: `services/agents/connectors/gmail.py`
- Create: `services/agents/connectors/google_calendar.py`
- Create: `services/agents/connectors/github.py`
- Create: `services/agents/connectors/whoop.py`
- Create: `services/agents/connectors/imap_email.py`
- Modify: `services/agents/main.py` — add sync + verify endpoints
- Modify: `services/agents/requirements.txt`

- [ ] **Step 1: Update requirements.txt**

```
fastapi==0.115.5
uvicorn[standard]==0.32.1
pydantic==2.10.3
anthropic==0.39.0
python-dotenv==1.0.1
httpx==0.28.1
supabase==2.10.0
google-auth==2.35.0
google-auth-oauthlib==1.2.1
google-api-python-client==2.154.0
PyGithub==2.5.0
```

Reinstall: `pip install -r requirements.txt`

- [ ] **Step 2: Create Gmail sync connector**

```python
# services/agents/connectors/gmail.py
import httpx
from datetime import datetime, timezone
from supabase import create_client
import os

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


async def refresh_google_token(refresh_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.post('https://oauth2.googleapis.com/token', data={
            'client_id': os.getenv('GOOGLE_CLIENT_ID'),
            'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
        })
        return r.json()


async def sync_gmail(user_id: str):
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # Get stored token
    res = sb.table('connector_tokens').select('*').eq('user_id', user_id).eq('connector', 'gmail').single().execute()
    if not res.data:
        return

    token_row = res.data
    access_token = token_row['access_token']

    # Refresh if expired
    expiry = datetime.fromisoformat(token_row['token_expiry'].replace('Z', '+00:00')) if token_row.get('token_expiry') else None
    if expiry and expiry < datetime.now(timezone.utc):
        new_tokens = await refresh_google_token(token_row['refresh_token'])
        access_token = new_tokens['access_token']
        new_expiry = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        sb.table('connector_tokens').update({
            'access_token': access_token,
            'token_expiry': new_expiry,
        }).eq('user_id', user_id).eq('connector', 'gmail').execute()

    # Mark syncing
    sb.table('connector_tokens').update({'sync_status': 'syncing'}).eq('user_id', user_id).eq('connector', 'gmail').execute()

    try:
        # Fetch recent threads (last 50)
        async with httpx.AsyncClient() as client:
            threads_res = await client.get(
                'https://gmail.googleapis.com/gmail/v1/users/me/threads',
                headers={'Authorization': f'Bearer {access_token}'},
                params={'maxResults': 50, 'q': 'newer_than:30d'},
            )
            threads = threads_res.json().get('threads', [])

        for thread in threads[:20]:  # Process top 20
            async with httpx.AsyncClient() as client:
                detail_res = await client.get(
                    f'https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread["id"]}',
                    headers={'Authorization': f'Bearer {access_token}'},
                    params={'format': 'metadata', 'metadataHeaders': ['From', 'Subject', 'Date']},
                )
            detail = detail_res.json()
            messages = detail.get('messages', [])
            if not messages:
                continue

            headers_map = {h['name']: h['value'] for h in messages[-1].get('payload', {}).get('headers', [])}
            subject = headers_map.get('Subject', '(no subject)')
            from_addr = headers_map.get('From', '')
            date_str = headers_map.get('Date', '')
            participants = list({m.get('payload', {}).get('headers', [{}])[0].get('value', '') for m in messages if m.get('payload', {}).get('headers')})

            try:
                last_msg_dt = datetime.strptime(date_str[:25], '%a, %d %b %Y %H:%M:%S').replace(tzinfo=timezone.utc).isoformat()
            except Exception:
                last_msg_dt = datetime.now(timezone.utc).isoformat()

            sb.table('lg_communications').upsert({
                'user_id': user_id,
                'thread_id': thread['id'],
                'channel': 'gmail',
                'participants': [from_addr],
                'subject': subject,
                'last_message_at': last_msg_dt,
                'status': 'active',
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }, on_conflict='user_id,thread_id').execute()

        sb.table('connector_tokens').update({
            'sync_status': 'ok',
            'last_synced_at': datetime.now(timezone.utc).isoformat(),
            'error_message': None,
        }).eq('user_id', user_id).eq('connector', 'gmail').execute()

    except Exception as e:
        sb.table('connector_tokens').update({
            'sync_status': 'error',
            'error_message': str(e)[:200],
        }).eq('user_id', user_id).eq('connector', 'gmail').execute()
        raise
```

- [ ] **Step 3: Create GitHub sync connector**

```python
# services/agents/connectors/github.py
import httpx
from datetime import datetime, timezone
from supabase import create_client
import os

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


async def sync_github(user_id: str):
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    res = sb.table('connector_tokens').select('*').eq('user_id', user_id).eq('connector', 'github').single().execute()
    if not res.data:
        return

    pat = res.data['access_token']
    username = res.data.get('extra', {}).get('username', '')
    headers = {'Authorization': f'token {pat}', 'User-Agent': 'chief-app'}

    sb.table('connector_tokens').update({'sync_status': 'syncing'}).eq('user_id', user_id).eq('connector', 'github').execute()

    try:
        async with httpx.AsyncClient() as client:
            repos_res = await client.get(
                f'https://api.github.com/users/{username}/repos',
                headers=headers,
                params={'sort': 'pushed', 'per_page': 20},
            )
            repos = repos_res.json()

        for repo in repos:
            if repo.get('fork'):
                continue
            pushed_at = repo.get('pushed_at')

            # Upsert as project
            sb.table('lg_projects').upsert({
                'user_id': user_id,
                'name': repo['name'],
                'type': 'github_repo',
                'status': 'active' if not repo.get('archived') else 'archived',
                'tools': ['github'],
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }, on_conflict='user_id,name').execute()

            # Fetch recent commits for top 5 repos
            if repos.index(repo) < 5:
                async with httpx.AsyncClient() as client:
                    commits_res = await client.get(
                        f'https://api.github.com/repos/{username}/{repo["name"]}/commits',
                        headers=headers,
                        params={'per_page': 10, 'author': username},
                    )
                    commits = commits_res.json() if commits_res.status_code == 200 else []

                for commit in commits:
                    commit_date = commit.get('commit', {}).get('author', {}).get('date', '')
                    message = commit.get('commit', {}).get('message', '')[:200]
                    sha = commit.get('sha', '')[:12]

                    sb.table('lg_health').upsert({
                        'user_id': user_id,
                        'metric': 'github_commit',
                        'value': {'repo': repo['name'], 'message': message, 'sha': sha},
                        'source': 'github',
                        'confidence': 'high',
                        'recorded_at': commit_date or datetime.now(timezone.utc).isoformat(),
                    }, on_conflict='user_id,metric,recorded_at').execute()

        sb.table('connector_tokens').update({
            'sync_status': 'ok',
            'last_synced_at': datetime.now(timezone.utc).isoformat(),
            'error_message': None,
        }).eq('user_id', user_id).eq('connector', 'github').execute()

    except Exception as e:
        sb.table('connector_tokens').update({
            'sync_status': 'error',
            'error_message': str(e)[:200],
        }).eq('user_id', user_id).eq('connector', 'github').execute()
        raise
```

- [ ] **Step 4: Create WHOOP sync connector**

```python
# services/agents/connectors/whoop.py
import httpx
from datetime import datetime, timezone
from supabase import create_client
import os

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
WHOOP_API = 'https://api.prod.whoop.com/developer/v1'


async def refresh_whoop_token(refresh_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.post('https://api.prod.whoop.com/oauth/oauth2/token', data={
            'client_id': os.getenv('WHOOP_CLIENT_ID'),
            'client_secret': os.getenv('WHOOP_CLIENT_SECRET'),
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
        })
        return r.json()


async def sync_whoop(user_id: str):
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    res = sb.table('connector_tokens').select('*').eq('user_id', user_id).eq('connector', 'whoop').single().execute()
    if not res.data:
        return

    token_row = res.data
    access_token = token_row['access_token']

    expiry = datetime.fromisoformat(token_row['token_expiry'].replace('Z', '+00:00')) if token_row.get('token_expiry') else None
    if expiry and expiry < datetime.now(timezone.utc):
        new_tokens = await refresh_whoop_token(token_row['refresh_token'])
        access_token = new_tokens['access_token']
        sb.table('connector_tokens').update({
            'access_token': access_token,
            'token_expiry': datetime.now(timezone.utc).isoformat(),
        }).eq('user_id', user_id).eq('connector', 'whoop').execute()

    sb.table('connector_tokens').update({'sync_status': 'syncing'}).eq('user_id', user_id).eq('connector', 'whoop').execute()
    headers = {'Authorization': f'Bearer {access_token}'}

    try:
        async with httpx.AsyncClient() as client:
            # Sleep data
            sleep_res = await client.get(f'{WHOOP_API}/activity/sleep', headers=headers, params={'limit': 7})
            sleeps = sleep_res.json().get('records', [])

            # Recovery data
            recovery_res = await client.get(f'{WHOOP_API}/recovery', headers=headers, params={'limit': 7})
            recoveries = recovery_res.json().get('records', [])

            # Workouts
            workout_res = await client.get(f'{WHOOP_API}/activity/workout', headers=headers, params={'limit': 10})
            workouts = workout_res.json().get('records', [])

        for sleep in sleeps:
            score = sleep.get('score', {})
            start = sleep.get('start', '')
            sb.table('lg_health').upsert({
                'user_id': user_id,
                'metric': 'sleep',
                'value': {
                    'duration_minutes': score.get('stage_summary', {}).get('total_in_bed_time_milli', 0) // 60000,
                    'efficiency_pct': score.get('sleep_efficiency_percentage', 0),
                    'quality': score.get('sleep_performance_percentage', 0),
                },
                'source': 'whoop',
                'confidence': 'high',
                'recorded_at': start or datetime.now(timezone.utc).isoformat(),
            }, on_conflict='user_id,metric,recorded_at').execute()

        for rec in recoveries:
            created = rec.get('created_at', '')
            score = rec.get('score', {})
            sb.table('lg_health').upsert({
                'user_id': user_id,
                'metric': 'recovery',
                'value': {
                    'recovery_score': score.get('recovery_score', 0),
                    'hrv_rmssd_milli': score.get('hrv_rmssd_milli', 0),
                    'resting_heart_rate': score.get('resting_heart_rate_bpm', 0),
                    'spo2_pct': score.get('spo2_percentage', 0),
                },
                'source': 'whoop',
                'confidence': 'high',
                'recorded_at': created or datetime.now(timezone.utc).isoformat(),
            }, on_conflict='user_id,metric,recorded_at').execute()

        for workout in workouts:
            start = workout.get('start', '')
            score = workout.get('score', {})
            sb.table('lg_health').upsert({
                'user_id': user_id,
                'metric': 'workout',
                'value': {
                    'sport_id': workout.get('sport_id', 0),
                    'strain': score.get('strain', 0),
                    'average_heart_rate': score.get('average_heart_rate_bpm', 0),
                    'max_heart_rate': score.get('max_heart_rate_bpm', 0),
                    'calories': score.get('kilojoule', 0) / 4.184,
                    'duration_minutes': (
                        (datetime.fromisoformat(workout.get('end', start).replace('Z', '+00:00')) -
                         datetime.fromisoformat(start.replace('Z', '+00:00'))).seconds // 60
                    ) if start else 0,
                },
                'source': 'whoop',
                'confidence': 'high',
                'recorded_at': start or datetime.now(timezone.utc).isoformat(),
            }, on_conflict='user_id,metric,recorded_at').execute()

        sb.table('connector_tokens').update({
            'sync_status': 'ok',
            'last_synced_at': datetime.now(timezone.utc).isoformat(),
            'error_message': None,
        }).eq('user_id', user_id).eq('connector', 'whoop').execute()

    except Exception as e:
        sb.table('connector_tokens').update({
            'sync_status': 'error',
            'error_message': str(e)[:200],
        }).eq('user_id', user_id).eq('connector', 'whoop').execute()
        raise
```

- [ ] **Step 5: Create IMAP uni email connector**

```python
# services/agents/connectors/imap_email.py
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timezone
from supabase import create_client
import os

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


def decode_str(s) -> str:
    if s is None:
        return ''
    parts = decode_header(s)
    result = []
    for part, enc in parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or 'utf-8', errors='replace'))
        else:
            result.append(str(part))
    return ' '.join(result)


def verify_imap(email_addr: str, password: str, imap_host: str, imap_port: int = 993) -> bool:
    try:
        mail = imaplib.IMAP4_SSL(imap_host, imap_port)
        mail.login(email_addr, password)
        mail.logout()
        return True
    except Exception:
        return False


async def sync_imap(user_id: str):
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    res = sb.table('connector_tokens').select('*').eq('user_id', user_id).eq('connector', 'imap_uni').single().execute()
    if not res.data:
        return

    token_row = res.data
    extra = token_row.get('extra', {})
    email_addr = extra.get('email', '')
    password = token_row['access_token']
    imap_host = extra.get('imap_host', '')
    imap_port = int(extra.get('imap_port', 993))

    sb.table('connector_tokens').update({'sync_status': 'syncing'}).eq('user_id', user_id).eq('connector', 'imap_uni').execute()

    try:
        mail = imaplib.IMAP4_SSL(imap_host, imap_port)
        mail.login(email_addr, password)
        mail.select('INBOX')

        # Fetch last 30 emails
        _, msg_nums = mail.search(None, 'ALL')
        all_nums = msg_nums[0].split()
        recent = all_nums[-30:] if len(all_nums) > 30 else all_nums

        for num in reversed(recent):
            _, data = mail.fetch(num, '(RFC822.SIZE BODY[HEADER.FIELDS (FROM TO SUBJECT DATE MESSAGE-ID)])')
            raw = data[0][1]
            msg = email.message_from_bytes(raw)

            subject = decode_str(msg.get('Subject', ''))
            from_addr = decode_str(msg.get('From', ''))
            date_str = msg.get('Date', '')
            msg_id = msg.get('Message-ID', str(num))

            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(date_str).astimezone(timezone.utc).isoformat()
            except Exception:
                dt = datetime.now(timezone.utc).isoformat()

            sb.table('lg_communications').upsert({
                'user_id': user_id,
                'thread_id': f'imap_{msg_id}',
                'channel': 'imap_uni',
                'participants': [from_addr],
                'subject': subject,
                'last_message_at': dt,
                'status': 'active',
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }, on_conflict='user_id,thread_id').execute()

        mail.logout()

        sb.table('connector_tokens').update({
            'sync_status': 'ok',
            'last_synced_at': datetime.now(timezone.utc).isoformat(),
            'error_message': None,
        }).eq('user_id', user_id).eq('connector', 'imap_uni').execute()

    except Exception as e:
        sb.table('connector_tokens').update({
            'sync_status': 'error',
            'error_message': str(e)[:200],
        }).eq('user_id', user_id).eq('connector', 'imap_uni').execute()
        raise
```

- [ ] **Step 6: Update main.py with sync and verify endpoints**

```python
# services/agents/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from models import ChatRequest, ChatResponse
from orchestrator import route_and_handle
from connectors.gmail import sync_gmail
from connectors.github import sync_github
from connectors.whoop import sync_whoop
from connectors.imap_email import sync_imap, verify_imap
import asyncio

load_dotenv()

app = FastAPI(title='Chief Agent Service', version='0.1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


class SyncRequest(BaseModel):
    user_id: str


class IMAPVerifyRequest(BaseModel):
    email: str
    password: str
    imap_host: str
    imap_port: int = 993


@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'chief-agents'}


@app.post('/chat', response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    return await route_and_handle(request)


@app.post('/sync/google')
async def sync_google(req: SyncRequest):
    asyncio.create_task(sync_gmail(req.user_id))
    return {'status': 'sync_started', 'connector': 'gmail'}


@app.post('/sync/github')
async def sync_github_route(req: SyncRequest):
    asyncio.create_task(sync_github(req.user_id))
    return {'status': 'sync_started', 'connector': 'github'}


@app.post('/sync/whoop')
async def sync_whoop_route(req: SyncRequest):
    asyncio.create_task(sync_whoop(req.user_id))
    return {'status': 'sync_started', 'connector': 'whoop'}


@app.post('/sync/imap_uni')
async def sync_imap_route(req: SyncRequest):
    asyncio.create_task(sync_imap(req.user_id))
    return {'status': 'sync_started', 'connector': 'imap_uni'}


@app.post('/connectors/imap/verify')
async def verify_imap_route(req: IMAPVerifyRequest):
    ok = verify_imap(req.email, req.password, req.imap_host, req.imap_port)
    if not ok:
        raise HTTPException(status_code=400, detail='IMAP connection failed — check host, credentials, and port.')
    return {'ok': True}
```

- [ ] **Step 7: Add Supabase env vars to agents .env**

```bash
# services/agents/.env — add these lines
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
ANTHROPIC_API_KEY=sk-ant-...
WHOOP_CLIENT_ID=your-whoop-client-id
WHOOP_CLIENT_SECRET=your-whoop-client-secret
```

- [ ] **Step 8: Commit**

```bash
cd C:/Users/Micha/chief
git add services/agents/
git commit -m "feat: add Gmail, GitHub, WHOOP, IMAP sync connectors in Python"
```

---

## Task 10: Today view — gated on real data

**Files:**
- Create: `apps/web/components/today/ConnectGate.tsx`
- Modify: `apps/web/app/(app)/today/page.tsx`
- Create: `apps/web/components/today/MorningBriefReal.tsx`

- [ ] **Step 1: Create ConnectGate component**

```tsx
// apps/web/components/today/ConnectGate.tsx
import Link from 'next/link';
import { Button } from '@/components/design-system';
import { Zap } from 'lucide-react';

export function ConnectGate() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center space-y-5 pb-16">
      <div className="w-14 h-14 rounded-full bg-[linear-gradient(135deg,#2633D9,#8A3AFF)] flex items-center justify-center">
        <Zap size={22} className="text-white" />
      </div>
      <div className="space-y-2 max-w-sm">
        <h2 className="text-lg font-semibold text-[var(--v2-text)]">Connect your first source</h2>
        <p className="text-[13px] text-[var(--v2-muted)] leading-relaxed">
          Chief needs at least Gmail connected to build your Morning Brief. Connect it in Settings — takes about 30 seconds.
        </p>
      </div>
      <Link href="/settings">
        <Button variant="solid" size="md">Go to Settings →</Button>
      </Link>
    </div>
  );
}
```

- [ ] **Step 2: Create MorningBriefReal — reads from DB**

```tsx
// apps/web/components/today/MorningBriefReal.tsx
import { Panel, StatusDot } from '@/components/design-system';
import { Activity, DollarSign, Briefcase, FileText } from 'lucide-react';

interface BriefData {
  body: { headline: string; detail: string; status: 'ok' | 'med' | 'high' | 'crit' } | null;
  work: { headline: string; detail: string; status: 'ok' | 'med' | 'high' | 'crit' } | null;
  admin: { headline: string; detail: string; status: 'ok' | 'med' | 'high' | 'crit' } | null;
}

export function MorningBriefReal({ data, greeting }: { data: BriefData; greeting: string }) {
  const sections = [
    data.body && { domain: 'body', label: 'Body', agent: 'Pulse', icon: Activity, ...data.body },
    data.work && { domain: 'work', label: 'Work', agent: 'Forge + Echo', icon: Briefcase, ...data.work },
    data.admin && { domain: 'admin', label: 'Admin', agent: 'Clerk', icon: FileText, ...data.admin },
  ].filter(Boolean) as any[];

  if (sections.length === 0) {
    return (
      <div className="text-[13px] text-[var(--v2-muted)]">
        Syncing your data... check back in a moment.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-[var(--v2-text)]">{greeting}</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {sections.map(s => {
          const Icon = s.icon;
          return (
            <Panel key={s.domain} className="p-4 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Icon size={14} className="text-[var(--v2-violet)]" />
                  <span className="text-[11px] uppercase tracking-[0.08em] font-semibold text-[var(--v2-muted)]">{s.label}</span>
                  <span className="text-[10px] text-[var(--v2-subtle)]">[{s.agent}]</span>
                </div>
                <StatusDot severity={s.status} size="xs" />
              </div>
              <p className="text-sm font-medium text-[var(--v2-text)]">{s.headline}</p>
              <p className="text-[12px] text-[var(--v2-muted)]">{s.detail}</p>
            </Panel>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Build real Today page — gate + real data**

```tsx
// apps/web/app/(app)/today/page.tsx
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { TopBar } from '@/components/layout/TopBar';
import { ConnectGate } from '@/components/today/ConnectGate';
import { MorningBriefReal } from '@/components/today/MorningBriefReal';
import { MomentumScore } from '@/components/today/MomentumScore';
import { ApprovalQueueServer } from '@/components/today/ApprovalQueueServer';

export default async function TodayPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect('/login');

  // Check if any connector is live
  const { data: tokens } = await supabase
    .from('connector_tokens')
    .select('connector, sync_status')
    .eq('user_id', user.id)
    .in('sync_status', ['ok', 'syncing']);

  const hasLiveConnector = (tokens ?? []).length > 0;

  // Fetch latest momentum score
  const { data: scoreRow } = await supabase
    .from('momentum_scores')
    .select('*')
    .eq('user_id', user.id)
    .order('scored_at', { ascending: false })
    .limit(1)
    .maybeSingle();

  // Fetch approval queue items
  const { data: queueItems } = await supabase
    .from('approval_queue')
    .select('*')
    .eq('user_id', user.id)
    .eq('status', 'pending')
    .order('created_at', { ascending: false })
    .limit(10);

  // Build brief data from real sources
  let briefData = { body: null, work: null, admin: null } as any;

  if (hasLiveConnector) {
    // Recovery data from WHOOP
    const { data: latestRecovery } = await supabase
      .from('lg_health')
      .select('value, recorded_at')
      .eq('user_id', user.id)
      .eq('metric', 'recovery')
      .order('recorded_at', { ascending: false })
      .limit(1)
      .maybeSingle();

    if (latestRecovery) {
      const score = (latestRecovery.value as any).recovery_score ?? 0;
      briefData.body = {
        headline: `Recovery ${score}%`,
        detail: score >= 67
          ? 'You\'re in the green. Train as planned.'
          : score >= 34
          ? 'Moderate recovery. Consider lighter intensity today.'
          : 'Low recovery. Rest or light movement recommended.',
        status: score >= 67 ? 'ok' : score >= 34 ? 'med' : 'high',
      };
    }

    // Stale communications from Echo/Forge
    const { data: staleComms } = await supabase
      .from('lg_communications')
      .select('subject, participants, last_message_at, staleness_days')
      .eq('user_id', user.id)
      .eq('status', 'active')
      .gte('staleness_days', 3)
      .order('staleness_days', { ascending: false })
      .limit(3);

    if (staleComms && staleComms.length > 0) {
      const top = staleComms[0];
      briefData.work = {
        headline: `${staleComms.length} thread${staleComms.length > 1 ? 's' : ''} need attention`,
        detail: `"${top.subject?.slice(0, 60)}" — ${top.staleness_days} days without reply.`,
        status: staleComms.some(c => c.staleness_days >= 7) ? 'high' : 'med',
      };
    }

    // Admin: pending queue items
    if (queueItems && queueItems.length > 0) {
      briefData.admin = {
        headline: `${queueItems.length} item${queueItems.length > 1 ? 's' : ''} in approval queue`,
        detail: queueItems[0].title,
        status: 'med',
      };
    }
  }

  const domains = scoreRow ? [
    { label: 'Body',       value: scoreRow.body ?? 0,       color: '#18E6D8' },
    { label: 'Money',      value: scoreRow.money ?? 0,      color: '#F7A93B' },
    { label: 'Work',       value: scoreRow.work ?? 0,       color: '#8A3AFF' },
    { label: 'Admin',      value: scoreRow.admin ?? 0,      color: '#38F2A8' },
    { label: 'Discipline', value: scoreRow.discipline ?? 0, color: '#3B82F6' },
  ] : [];

  const hour = new Date().getHours();
  const greeting =
    hour < 12 ? 'Good morning, Mohamed.' :
    hour < 18 ? 'Good afternoon, Mohamed.' :
                'Good evening, Mohamed.';

  return (
    <>
      <TopBar title="Today" momentumScore={scoreRow?.total} />
      <main className="flex-1 overflow-y-auto p-4 max-w-3xl">
        {!hasLiveConnector ? (
          <ConnectGate />
        ) : (
          <div className="space-y-5">
            {scoreRow && <MomentumScore total={scoreRow.total} domains={domains} />}
            <MorningBriefReal data={briefData} greeting={greeting} />
            <ApprovalQueueServer items={queueItems ?? []} userId={user.id} />
          </div>
        )}
      </main>
    </>
  );
}
```

- [ ] **Step 4: Create ApprovalQueueServer wrapper**

```tsx
// apps/web/components/today/ApprovalQueueServer.tsx
'use client';
import { useState } from 'react';
import { ApprovalQueue } from './ApprovalQueue';
import { toast } from 'sonner';

interface QueueRow {
  id: string;
  agent: string;
  title: string;
  description: string;
  risk_level: 'auto' | 'notify' | 'approve' | 'confirm';
}

export function ApprovalQueueServer({ items, userId }: { items: QueueRow[]; userId: string }) {
  const [localItems, setLocalItems] = useState(
    items.map(i => ({ ...i, riskLevel: i.risk_level }))
  );

  async function handleApprove(id: string) {
    const item = localItems.find(i => i.id === id);
    setLocalItems(prev => prev.filter(i => i.id !== id));
    await fetch('/api/queue/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id }),
    });
    toast.success(`Approved: ${item?.title}`);
  }

  async function handleReject(id: string) {
    const item = localItems.find(i => i.id === id);
    setLocalItems(prev => prev.filter(i => i.id !== id));
    await fetch('/api/queue/reject', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id }),
    });
    toast(`Skipped: ${item?.title}`);
  }

  return (
    <ApprovalQueue
      items={localItems}
      onApprove={handleApprove}
      onReject={handleReject}
    />
  );
}
```

- [ ] **Step 5: Create queue approve/reject API routes**

```ts
// apps/web/app/api/queue/approve/route.ts
import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function POST(request: Request) {
  const { id } = await request.json();
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  await supabase.from('approval_queue')
    .update({ status: 'approved' })
    .eq('id', id)
    .eq('user_id', user.id);

  return NextResponse.json({ ok: true });
}
```

```ts
// apps/web/app/api/queue/reject/route.ts
import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function POST(request: Request) {
  const { id } = await request.json();
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  await supabase.from('approval_queue')
    .update({ status: 'rejected' })
    .eq('id', id)
    .eq('user_id', user.id);

  return NextResponse.json({ ok: true });
}
```

- [ ] **Step 6: Commit**

```bash
cd C:/Users/Micha/chief
git add apps/web/
git commit -m "feat: Today view gated on real connector data, no stubs"
```

---

## Verification

1. Run `npm run dev:web` + `uvicorn main:app --reload --port 8001` in `services/agents`
2. Navigate to `/today` — should show ConnectGate (no connectors yet)
3. Navigate to `/settings` — click **Connect** on Gmail → Google OAuth → returns to `/settings?connected=google`
4. Check Supabase `connector_tokens` table — row appears with `sync_status: 'ok'`
5. Check `lg_communications` table — Gmail threads populated
6. Navigate to `/today` — Morning Brief appears with real stale thread data
7. Connect GitHub PAT — check `lg_projects` table populated with your repos
8. Connect WHOOP — check `lg_health` table populated with sleep/recovery rows
9. Connect uni IMAP — check `lg_communications` for `channel: 'imap_uni'` rows
10. Chat to `/chat` — ask "What stale emails do I have?" — Forge/Echo should answer from real DB data
