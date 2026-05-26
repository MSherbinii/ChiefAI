# Chief Phase 0 — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold a working monorepo with a Next.js 15 web app (auth + base UI shell with Today, Chat, Settings views), a Python FastAPI agent service (basic Chief orchestrator), and a Supabase database with the full Life Graph schema — all wired together and runnable locally.

**Architecture:** Two services in one monorepo: `apps/web` (Next.js 15 App Router, Lumina V2 design system ported) and `services/agents` (Python FastAPI, basic orchestrator that routes to stub agents). Next.js API routes act as a gateway — the browser never talks to the Python service directly. Supabase provides auth, Postgres, realtime, and storage.

**Tech Stack:** Next.js 15 (App Router), Supabase JS v2, Python 3.11+ / FastAPI, Tailwind CSS v3, Framer Motion 12, Radix UI primitives, Bai Jamjuree + JetBrains Mono fonts, Zod v4, Zustand v5, React 19, TypeScript 5.

---

## Monorepo File Map

```
chief/                              ← renamed from jarvisAI
├── apps/
│   └── web/                        ← Next.js 15 web app
│       ├── app/
│       │   ├── layout.tsx           ← root layout, theme, fonts, Toaster
│       │   ├── page.tsx             ← redirect → /today
│       │   ├── (auth)/
│       │   │   ├── login/page.tsx   ← sign in page
│       │   │   └── callback/route.ts ← Supabase OAuth callback
│       │   └── (app)/
│       │       ├── layout.tsx       ← app shell: sidebar + top bar
│       │       ├── today/page.tsx   ← Today view (Morning Brief + queue)
│       │       ├── chat/page.tsx    ← Chat view
│       │       └── settings/page.tsx ← Settings view
│       ├── components/
│       │   ├── design-system/
│       │   │   ├── tokens.css       ← ported Lumina V2 CSS variables
│       │   │   ├── Button.tsx       ← ported from Lumina
│       │   │   ├── Panel.tsx        ← ported from Lumina
│       │   │   ├── StatusDot.tsx    ← ported + simplified (no MachineLifecycle dep)
│       │   │   └── index.ts         ← barrel export
│       │   ├── layout/
│       │   │   ├── Sidebar.tsx      ← navigation: Today, Chat, Domains, Graph, Replay, Settings
│       │   │   └── TopBar.tsx       ← user avatar, momentum score pill, notifications
│       │   ├── today/
│       │   │   ├── MorningBrief.tsx ← brief card with domain sections
│       │   │   ├── MomentumScore.tsx ← score ring + domain breakdown
│       │   │   └── ApprovalQueue.tsx ← queued action cards
│       │   └── chat/
│       │       ├── ChatPanel.tsx    ← message list + input
│       │       ├── Message.tsx      ← user/assistant message bubble
│       │       └── ChatInput.tsx    ← text input + send button
│       ├── lib/
│       │   ├── supabase/
│       │   │   ├── client.ts        ← browser Supabase client (singleton)
│       │   │   └── server.ts        ← server Supabase client (cookies)
│       │   └── cn.ts                ← clsx + tailwind-merge helper
│       ├── store/
│       │   └── ui.ts                ← Zustand: sidebar open, active view, chat messages
│       ├── app/api/
│       │   └── chat/route.ts        ← POST /api/chat → forwards to Python agent service
│       ├── middleware.ts            ← Supabase auth middleware (protect /app routes)
│       ├── next.config.ts
│       ├── tailwind.config.ts
│       ├── tsconfig.json
│       └── package.json
├── services/
│   └── agents/                     ← Python FastAPI agent service
│       ├── main.py                  ← FastAPI app, CORS, routes
│       ├── orchestrator.py          ← Chief orchestrator: routes message → agent
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── base.py              ← BaseAgent ABC: name, handle(message, context)
│       │   ├── pulse.py             ← Pulse stub (health domain)
│       │   ├── echo.py              ← Echo stub (communication domain)
│       │   └── forge.py             ← Forge stub (projects domain)
│       ├── models.py                ← Pydantic request/response models
│       ├── requirements.txt
│       └── .env.example
├── supabase/
│   └── migrations/
│       └── 0001_life_graph_schema.sql ← full Life Graph schema
├── .env.example                    ← root env template
└── package.json                    ← root scripts (dev, build)
```

---

## Task 1: Rename directory and init monorepo root

**Files:**
- Create: `chief/package.json`
- Create: `chief/.env.example`
- Create: `chief/.gitignore`

- [ ] **Step 1: Rename jarvisAI → chief**

```bash
mv C:/Users/Micha/jarvisAI C:/Users/Micha/chief
cd C:/Users/Micha/chief
```

- [ ] **Step 2: Create root package.json**

```bash
cat > package.json << 'EOF'
{
  "name": "chief",
  "private": true,
  "workspaces": ["apps/*", "services/*"],
  "scripts": {
    "dev:web": "cd apps/web && npm run dev",
    "dev:agents": "cd services/agents && uvicorn main:app --reload --port 8001",
    "dev": "concurrently \"npm run dev:web\" \"npm run dev:agents\"",
    "build:web": "cd apps/web && npm run build"
  },
  "devDependencies": {
    "concurrently": "^8.2.2"
  }
}
EOF
```

- [ ] **Step 3: Create .env.example**

```bash
cat > .env.example << 'EOF'
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Python agent service (called from Next.js API routes)
AGENT_SERVICE_URL=http://localhost:8001

# ElevenLabs (Phase 1)
ELEVENLABS_API_KEY=

# Deepgram (Phase 1)
DEEPGRAM_API_KEY=
EOF
```

- [ ] **Step 4: Create .gitignore**

```bash
cat > .gitignore << 'EOF'
node_modules/
.next/
.env
.env.local
__pycache__/
*.pyc
.venv/
dist/
.DS_Store
EOF
```

- [ ] **Step 5: Commit**

```bash
git init
git add .
git commit -m "chore: init chief monorepo"
```

---

## Task 2: Scaffold Next.js web app

**Files:**
- Create: `apps/web/` (full Next.js 15 project)

- [ ] **Step 1: Create the Next.js app**

```bash
cd C:/Users/Micha/chief
mkdir -p apps
cd apps
npx create-next-app@latest web \
  --typescript \
  --tailwind \
  --app \
  --src-dir=false \
  --import-alias="@/*" \
  --no-eslint
cd web
```

- [ ] **Step 2: Install dependencies**

```bash
npm install \
  @supabase/supabase-js @supabase/ssr \
  framer-motion \
  zustand \
  zod \
  sonner \
  lucide-react \
  clsx tailwind-merge \
  @radix-ui/react-dialog \
  @radix-ui/react-dropdown-menu \
  @radix-ui/react-tooltip \
  @radix-ui/react-scroll-area \
  @radix-ui/react-separator \
  @radix-ui/react-slot \
  @fontsource/bai-jamjuree \
  @fontsource/jetbrains-mono \
  class-variance-authority
```

- [ ] **Step 3: Verify app starts**

```bash
npm run dev
```

Expected: Next.js dev server running at http://localhost:3000 with default page.

- [ ] **Step 4: Commit**

```bash
cd C:/Users/Micha/chief
git add apps/web/
git commit -m "feat: scaffold Next.js 15 web app"
```

---

## Task 3: Port Lumina design system

**Files:**
- Create: `apps/web/components/design-system/tokens.css`
- Create: `apps/web/components/design-system/Button.tsx`
- Create: `apps/web/components/design-system/Panel.tsx`
- Create: `apps/web/components/design-system/StatusDot.tsx`
- Create: `apps/web/components/design-system/index.ts`
- Create: `apps/web/lib/cn.ts`
- Modify: `apps/web/app/globals.css`
- Modify: `apps/web/app/layout.tsx`
- Modify: `apps/web/tailwind.config.ts`

- [ ] **Step 1: Create cn utility**

```ts
// apps/web/lib/cn.ts
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 2: Create design tokens CSS**

```css
/* apps/web/components/design-system/tokens.css */
[data-theme='chief'] {
  /* Surfaces */
  --v2-base:        #050608;
  --v2-bg-soft:     #080A0E;
  --v2-sidebar:     #080B10;
  --v2-panel:       #0C1017;
  --v2-card:        #10151E;
  --v2-card-hover:  #141B26;
  --v2-elevated:    #171E2B;
  --v2-glass:       rgba(12, 16, 23, 0.82);
  --v2-glass-hi:    rgba(20, 27, 38, 0.88);

  /* Borders */
  --v2-border:         rgba(247, 240, 255, 0.10);
  --v2-border-strong:  rgba(247, 240, 255, 0.16);
  --v2-border-brand:   rgba(138, 58, 255, 0.38);
  --v2-border-mid:     rgba(138, 58, 255, 0.20);
  --v2-border-focus:   rgba(138, 58, 255, 0.65);

  /* Text */
  --v2-text:       #F7F0FF;
  --v2-text-dim:   rgba(247, 240, 255, 0.74);
  --v2-muted:      rgba(247, 240, 255, 0.52);
  --v2-subtle:     rgba(247, 240, 255, 0.36);

  /* Brand */
  --v2-violet:      #8A3AFF;
  --v2-violet-soft: #6F58FF;
  --v2-accent:      #8A3AFF;
  --v2-teal:        #18E6D8;
  --v2-ok:          #38F2A8;
  --v2-warn:        #F7A93B;
  --v2-crit:        #FF4F6D;
  --v2-danger:      #FF4F6D;
  --v2-info:        #3B82F6;

  /* Shadows */
  --v2-shadow-card:  0 18px 55px rgba(0, 0, 0, 0.38);
  --v2-shadow-soft:  0 10px 30px rgba(0, 0, 0, 0.28);
  --v2-shadow-brand: 0 0 28px rgba(89, 74, 255, 0.12);
  --v2-shadow-card-inset:
    inset 0 1px 0 rgba(255, 255, 255, 0.035),
    0 18px 55px rgba(0, 0, 0, 0.38);
  --v2-glow-violet:  0 0 24px rgba(89, 74, 255, 0.28);
  --v2-glow-teal:    0 0 24px rgba(24, 230, 216, 0.18);
  --v2-glow-ok:      0 0 8px rgba(56, 242, 168, 0.36);
  --v2-glow-warn:    0 0 8px rgba(247, 169, 59, 0.36);
  --v2-glow-crit:    0 0 8px rgba(255, 79, 109, 0.36);

  /* App background */
  --v2-app-bg:
    radial-gradient(circle at 18% 0%, rgba(38,99,235,0.05), transparent 30%),
    radial-gradient(circle at 76% 0%, rgba(138,58,255,0.045), transparent 32%),
    radial-gradient(circle at 95% 60%, rgba(24,230,216,0.02), transparent 26%),
    linear-gradient(180deg, #08090D 0%, #060608 52%, #060608 100%);

  /* Gradients */
  --v2-gradient-accent:  linear-gradient(135deg, #8A3AFF 0%, #2563EB 100%);
  --v2-gradient-card:    linear-gradient(180deg, rgba(18,24,34,0.98), rgba(11,15,22,0.98));

  /* Radius */
  --v2-radius-sm: 8px;
  --v2-radius-md: 12px;
  --v2-radius-lg: 16px;
  --v2-radius-xl: 20px;

  /* shadcn compat */
  --background: 222 30% 4%;
  --foreground: 270 100% 98%;
  --card: 222 28% 8%;
  --card-foreground: 270 100% 98%;
  --popover: 222 28% 8%;
  --popover-foreground: 270 100% 98%;
  --primary: 270 100% 61%;
  --primary-foreground: 222 30% 4%;
  --secondary: 222 25% 11%;
  --secondary-foreground: 270 100% 98%;
  --muted: 222 22% 11%;
  --muted-foreground: 270 30% 62%;
  --accent: 270 100% 61%;
  --accent-foreground: 222 30% 4%;
  --destructive: 349 100% 65%;
  --destructive-foreground: 270 100% 98%;
  --border: 222 18% 16%;
  --input: 222 18% 16%;
  --ring: 270 100% 61%;
  --radius: 0.75rem;

  background: var(--v2-app-bg);
  min-height: 100vh;
  color: var(--v2-text);
  font-family: 'Bai Jamjuree', 'Inter', ui-sans-serif, system-ui, sans-serif;
  font-size: 14px;
  font-weight: 400;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

[data-theme='chief'] [class*='font-mono'],
[data-theme='chief'] code,
[data-theme='chief'] pre {
  font-family: 'JetBrains Mono', ui-monospace, monospace !important;
}

/* Specular highlight on cards */
.chief-specular::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(180deg, rgba(255,255,255,0.028) 0%, transparent 40%);
  pointer-events: none;
}

/* Pulse animation for status dots */
@keyframes chief-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.85); }
}
.chief-pulse { animation: chief-pulse 1.6s ease-in-out infinite; }
```

- [ ] **Step 3: Create Button component**

```tsx
// apps/web/components/design-system/Button.tsx
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { cn } from '@/lib/cn';

type Variant = 'solid' | 'outline' | 'ghost' | 'danger';
type Size = 'xs' | 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  iconLeft?: ReactNode;
  iconRight?: ReactNode;
  loading?: boolean;
}

const VARIANTS: Record<Variant, string> = {
  solid: [
    'bg-[linear-gradient(135deg,#2633D9_0%,#8A3AFF_100%)]',
    'text-white font-semibold',
    'border border-[rgba(138,58,255,0.32)]',
    'shadow-[inset_0_1px_0_rgba(255,255,255,0.09),0_0_24px_rgba(89,74,255,0.24),0_4px_12px_rgba(0,0,0,0.30)]',
    'hover:brightness-110 active:brightness-95',
  ].join(' '),
  outline: [
    'bg-[rgba(247,240,255,0.04)] text-[var(--v2-text-dim)]',
    'border border-[rgba(247,240,255,0.12)]',
    'hover:bg-[rgba(247,240,255,0.07)] hover:border-[rgba(247,240,255,0.18)] hover:text-[var(--v2-text)]',
  ].join(' '),
  ghost: [
    'bg-transparent border-transparent text-[var(--v2-muted)]',
    'hover:bg-[rgba(247,240,255,0.05)] hover:text-[var(--v2-text-dim)]',
  ].join(' '),
  danger: [
    'bg-[rgba(255,79,109,0.10)] text-[var(--v2-danger)]',
    'border border-[rgba(255,79,109,0.24)]',
    'hover:bg-[rgba(255,79,109,0.16)] hover:border-[rgba(255,79,109,0.38)]',
  ].join(' '),
};

const SIZES: Record<Size, string> = {
  xs: 'h-6  px-2    text-[11px] gap-1   rounded-[8px]',
  sm: 'h-7  px-2.5  text-[12px] gap-1.5 rounded-[8px]',
  md: 'h-8  px-3.5  text-[13px] gap-2   rounded-[10px]',
  lg: 'h-10 px-5    text-[14px] gap-2   rounded-[12px]',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'outline', size = 'md', iconLeft, iconRight, loading, disabled, children, ...rest }, ref) => (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        'inline-flex items-center justify-center font-semibold tracking-[0.01em]',
        'select-none whitespace-nowrap transition-all duration-100',
        'disabled:opacity-40 disabled:cursor-not-allowed',
        'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--v2-border-focus)]',
        VARIANTS[variant],
        SIZES[size],
        className
      )}
      {...rest}
    >
      {loading ? (
        <svg className="animate-spin" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <circle cx="12" cy="12" r="10" strokeOpacity="0.25"/>
          <path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round"/>
        </svg>
      ) : iconLeft}
      {children}
      {!loading && iconRight}
    </button>
  )
);
Button.displayName = 'Button';
```

- [ ] **Step 4: Create Panel component**

```tsx
// apps/web/components/design-system/Panel.tsx
import { forwardRef, type HTMLAttributes } from 'react';
import { cn } from '@/lib/cn';

type Variant = 'default' | 'elevated' | 'inset' | 'ghost';

interface PanelProps extends HTMLAttributes<HTMLDivElement> {
  variant?: Variant;
  interactive?: boolean;
}

const VARIANTS: Record<Variant, string> = {
  default: [
    'border border-[rgba(247,240,255,0.10)]',
    '[background:linear-gradient(180deg,rgba(18,24,34,0.98),rgba(11,15,22,0.98))]',
  ].join(' '),
  elevated: [
    'border border-[rgba(247,240,255,0.14)]',
    '[background:linear-gradient(180deg,rgba(23,30,43,0.98),rgba(14,19,28,0.98))]',
  ].join(' '),
  inset: [
    'border border-[rgba(247,240,255,0.07)]',
    'bg-[rgba(8,11,17,0.95)]',
  ].join(' '),
  ghost: 'bg-transparent border border-transparent',
};

export const Panel = forwardRef<HTMLDivElement, PanelProps>(
  ({ className, variant = 'default', interactive, children, ...rest }, ref) => (
    <div
      ref={ref}
      className={cn(
        'rounded-[16px] relative overflow-hidden chief-specular',
        VARIANTS[variant],
        variant !== 'ghost' && 'shadow-[inset_0_1px_0_rgba(255,255,255,0.035),0_18px_55px_rgba(0,0,0,0.38)]',
        interactive && [
          'cursor-pointer select-none transition-all duration-150',
          'hover:border-[rgba(247,240,255,0.16)]',
          'hover:[background:linear-gradient(180deg,rgba(22,29,41,0.98),rgba(13,18,26,0.98))]',
          'hover:shadow-[inset_0_1px_0_rgba(255,255,255,0.04),0_0_0_1px_rgba(138,58,255,0.14),0_20px_50px_rgba(0,0,0,0.42)]',
          'active:scale-[0.998] active:duration-75',
        ].join(' '),
        className
      )}
      {...rest}
    >
      {children}
    </div>
  )
);
Panel.displayName = 'Panel';
```

- [ ] **Step 5: Create StatusDot component**

```tsx
// apps/web/components/design-system/StatusDot.tsx
import { cn } from '@/lib/cn';

type Severity = 'ok' | 'info' | 'low' | 'med' | 'high' | 'crit';

const SEVERITY: Record<Severity, { color: string; label: string; pulse: boolean }> = {
  ok:   { color: 'bg-[var(--v2-ok)] shadow-[0_0_8px_rgba(41,244,199,0.6)]',      label: 'OK',   pulse: false },
  info: { color: 'bg-[var(--v2-info)]',                                           label: 'Info', pulse: false },
  low:  { color: 'bg-[var(--v2-info)]',                                           label: 'Low',  pulse: false },
  med:  { color: 'bg-[var(--v2-violet)] shadow-[0_0_10px_rgba(138,58,255,0.6)]', label: 'Med',  pulse: false },
  high: { color: 'bg-[var(--v2-warn)] shadow-[0_0_10px_rgba(247,169,59,0.7)]',   label: 'High', pulse: true  },
  crit: { color: 'bg-[var(--v2-crit)] shadow-[0_0_12px_rgba(255,79,109,0.7)]',   label: 'Crit', pulse: true  },
};

const SIZES = { xs: 'w-1.5 h-1.5', sm: 'w-2 h-2', md: 'w-2.5 h-2.5' };

interface StatusDotProps {
  severity?: Severity;
  size?: 'xs' | 'sm' | 'md';
  showLabel?: boolean;
  className?: string;
}

export function StatusDot({ severity = 'ok', size = 'sm', showLabel, className }: StatusDotProps) {
  const s = SEVERITY[severity];
  return (
    <span className={cn('inline-flex items-center gap-2', className)}>
      <span className={cn('rounded-full', SIZES[size], s.color, s.pulse && 'chief-pulse')} />
      {showLabel && (
        <span className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-text-dim)]">
          {s.label}
        </span>
      )}
    </span>
  );
}
```

- [ ] **Step 6: Create barrel export**

```ts
// apps/web/components/design-system/index.ts
export { Button } from './Button';
export { Panel } from './Panel';
export { StatusDot } from './StatusDot';
```

- [ ] **Step 7: Update globals.css to import tokens and fonts**

Replace `apps/web/app/globals.css` with:

```css
@import '../components/design-system/tokens.css';
@import '@fontsource/bai-jamjuree/400.css';
@import '@fontsource/bai-jamjuree/500.css';
@import '@fontsource/bai-jamjuree/600.css';
@import '@fontsource/bai-jamjuree/700.css';
@import '@fontsource/jetbrains-mono/400.css';
@import '@fontsource/jetbrains-mono/500.css';

@tailwind base;
@tailwind components;
@tailwind utilities;

* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; }
```

- [ ] **Step 8: Update root layout to apply theme**

```tsx
// apps/web/app/layout.tsx
import type { Metadata } from 'next';
import { Toaster } from 'sonner';
import './globals.css';

export const metadata: Metadata = {
  title: 'Chief',
  description: 'Your life, under management.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="chief">
      <body>
        {children}
        <Toaster
          theme="dark"
          toastOptions={{
            style: {
              background: 'var(--v2-panel)',
              border: '1px solid var(--v2-border)',
              color: 'var(--v2-text)',
            },
          }}
        />
      </body>
    </html>
  );
}
```

- [ ] **Step 9: Verify design tokens render**

Run `npm run dev` in `apps/web`. Open http://localhost:3000. Background should be near-black (#060608) with the subtle brand gradient visible in the upper area.

- [ ] **Step 10: Commit**

```bash
cd C:/Users/Micha/chief
git add apps/web/
git commit -m "feat: port Lumina V2 design system to Chief"
```

---

## Task 4: Supabase project setup and Life Graph schema

**Files:**
- Create: `supabase/migrations/0001_life_graph_schema.sql`

- [ ] **Step 1: Create a new Supabase project**

1. Go to https://supabase.com/dashboard and create a new project named `chief`.
2. Copy the Project URL and anon key.
3. Create `apps/web/.env.local`:

```
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
AGENT_SERVICE_URL=http://localhost:8001
ANTHROPIC_API_KEY=sk-ant-...
```

- [ ] **Step 2: Write the Life Graph migration SQL**

```sql
-- supabase/migrations/0001_life_graph_schema.sql
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
  relationship     text,          -- 'professor', 'cofounder', 'landlord', etc.
  context          text,          -- free-form notes
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
  type        text,               -- 'thesis', 'startup', 'personal', 'client'
  status      text default 'active', -- 'active', 'paused', 'done', 'archived'
  deadline    date,
  tools       text[],             -- ['github', 'notion', 'drive']
  embedding   vector(1536),
  created_at  timestamptz default now(),
  updated_at  timestamptz default now()
);
alter table public.lg_projects enable row level security;
create policy "Users own their projects"
  on public.lg_projects for all
  using (auth.uid() = user_id);

-- ─── Life Graph: Health entries ───────────────────────────────────────────
create table public.lg_health (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references public.profiles(id) on delete cascade,
  metric      text not null,      -- 'sleep_hours', 'recovery_pct', 'weight_kg', 'workout', 'nutrition'
  value       jsonb not null,     -- flexible: { hours: 6.5 } or { calories: 2100, protein: 120 }
  source      text,               -- 'whoop', 'manual', 'apple_health'
  confidence  text default 'high', -- 'high', 'medium', 'low' (for photo estimates)
  recorded_at timestamptz not null,
  created_at  timestamptz default now()
);
alter table public.lg_health enable row level security;
create policy "Users own their health"
  on public.lg_health for all
  using (auth.uid() = user_id);

-- ─── Life Graph: Finance entries ──────────────────────────────────────────
create table public.lg_finance (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.profiles(id) on delete cascade,
  account         text,           -- 'sparkasse', 'revolut', 'n26', 'wise'
  type            text not null,  -- 'transaction', 'balance', 'subscription'
  amount_cents    bigint,
  currency        text default 'EUR',
  description     text,
  category        text,           -- 'food', 'transport', 'subscription', 'rent'
  is_subscription boolean default false,
  recurring_period text,          -- 'monthly', 'yearly'
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
  thread_id       text,           -- external thread id (Gmail thread id, etc)
  channel         text not null,  -- 'gmail', 'outlook', 'whatsapp'
  participants    text[],         -- email addresses or names
  subject         text,
  summary         text,           -- AI-generated thread summary
  last_message_at timestamptz,
  status          text default 'active', -- 'active', 'stale', 'resolved'
  staleness_days  integer generated always as (
    extract(day from now() - last_message_at)::integer
  ) stored,
  urgency         text default 'normal', -- 'low', 'normal', 'high', 'urgent'
  related_person_id uuid references public.lg_people(id),
  related_project_id uuid references public.lg_projects(id),
  embedding       vector(1536),
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);
alter table public.lg_communications enable row level security;
create policy "Users own their communications"
  on public.lg_communications for all
  using (auth.uid() = user_id);

-- ─── Life Graph: Documents ────────────────────────────────────────────────
create table public.lg_documents (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.profiles(id) on delete cascade,
  type            text not null,  -- 'insurance_card', 'id', 'contract', 'letter', 'receipt'
  title           text,
  extracted_fields jsonb,         -- { insurance_number: '...', valid_until: '...' }
  source          text,           -- 'upload', 'email_attachment'
  storage_path    text,           -- Supabase Storage path
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
  domain      text not null,      -- 'health', 'finance', 'work', 'admin', 'personal'
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
  agent        text not null,     -- 'pulse', 'echo', 'ledger', 'forge', 'clerk'
  action_type  text not null,     -- 'send_email', 'cancel_subscription', 'log_workout'
  risk_level   text default 'approve', -- 'auto', 'notify', 'approve', 'confirm'
  title        text not null,
  description  text,
  payload      jsonb,             -- full action data
  context_capsule jsonb,          -- data sources + reasoning
  status       text default 'pending', -- 'pending', 'approved', 'rejected', 'executed', 'expired'
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
  agent       text,               -- which sub-agent generated this ('pulse', 'echo', etc)
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
```

- [ ] **Step 3: Apply migration via Supabase SQL editor**

In the Supabase dashboard → SQL editor, paste and run the entire migration file. Verify all tables appear in the Table Editor.

- [ ] **Step 4: Commit migration**

```bash
cd C:/Users/Micha/chief
git add supabase/
git commit -m "feat: add Life Graph schema migration"
```

---

## Task 5: Supabase auth wiring in Next.js

**Files:**
- Create: `apps/web/lib/supabase/client.ts`
- Create: `apps/web/lib/supabase/server.ts`
- Create: `apps/web/middleware.ts`
- Create: `apps/web/app/(auth)/login/page.tsx`
- Create: `apps/web/app/(auth)/callback/route.ts`

- [ ] **Step 1: Create browser Supabase client**

```ts
// apps/web/lib/supabase/client.ts
import { createBrowserClient } from '@supabase/ssr';

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
```

- [ ] **Step 2: Create server Supabase client**

```ts
// apps/web/lib/supabase/server.ts
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';

export async function createClient() {
  const cookieStore = await cookies();
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() { return cookieStore.getAll(); },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            );
          } catch {}
        },
      },
    }
  );
}
```

- [ ] **Step 3: Create auth middleware to protect /app routes**

```ts
// apps/web/middleware.ts
import { createServerClient } from '@supabase/ssr';
import { NextResponse, type NextRequest } from 'next/server';

export async function middleware(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() { return request.cookies.getAll(); },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const { data: { user } } = await supabase.auth.getUser();

  if (!user && request.nextUrl.pathname.startsWith('/today') ||
      !user && request.nextUrl.pathname.startsWith('/chat') ||
      !user && request.nextUrl.pathname.startsWith('/settings')) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  return supabaseResponse;
}

export const config = {
  matcher: ['/today/:path*', '/chat/:path*', '/settings/:path*'],
};
```

- [ ] **Step 4: Create login page**

```tsx
// apps/web/app/(auth)/login/page.tsx
'use client';
import { useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { Button } from '@/components/design-system';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const supabase = createClient();

  async function handleMagicLink(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${location.origin}/callback` },
    });
    setSent(true);
    setLoading(false);
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-[var(--v2-text)]">Chief</h1>
          <p className="text-[var(--v2-muted)] text-sm">Your life, under management.</p>
        </div>
        {sent ? (
          <p className="text-[var(--v2-text-dim)] text-sm">
            Check your email — magic link sent to <strong>{email}</strong>.
          </p>
        ) : (
          <form onSubmit={handleMagicLink} className="space-y-3">
            <input
              type="email"
              placeholder="your@email.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              className="w-full h-10 px-3.5 rounded-[10px] bg-[rgba(247,240,255,0.04)] border border-[rgba(247,240,255,0.12)] text-[var(--v2-text)] placeholder:text-[var(--v2-subtle)] text-sm focus:outline-none focus:border-[var(--v2-border-focus)]"
            />
            <Button variant="solid" size="lg" className="w-full" loading={loading} type="submit">
              Send magic link
            </Button>
          </form>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Create OAuth callback route**

```ts
// apps/web/app/(auth)/callback/route.ts
import { createClient } from '@/lib/supabase/server';
import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get('code');

  if (code) {
    const supabase = await createClient();
    await supabase.auth.exchangeCodeForSession(code);
  }

  return NextResponse.redirect(`${origin}/today`);
}
```

- [ ] **Step 6: Test auth flow**

1. Run `npm run dev` in `apps/web`
2. Navigate to http://localhost:3000/today — should redirect to /login
3. Enter your email, click send
4. Click magic link in email — should land on /today (empty page for now)

- [ ] **Step 7: Commit**

```bash
cd C:/Users/Micha/chief
git add apps/web/
git commit -m "feat: add Supabase auth with magic link and middleware"
```

---

## Task 6: App shell layout (sidebar + top bar)

**Files:**
- Create: `apps/web/store/ui.ts`
- Create: `apps/web/components/layout/Sidebar.tsx`
- Create: `apps/web/components/layout/TopBar.tsx`
- Create: `apps/web/app/(app)/layout.tsx`
- Create: `apps/web/app/page.tsx`

- [ ] **Step 1: Create UI store**

```ts
// apps/web/store/ui.ts
import { create } from 'zustand';

interface UIStore {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
}

export const useUIStore = create<UIStore>(set => ({
  sidebarOpen: true,
  setSidebarOpen: open => set({ sidebarOpen: open }),
  toggleSidebar: () => set(s => ({ sidebarOpen: !s.sidebarOpen })),
}));
```

- [ ] **Step 2: Create Sidebar**

```tsx
// apps/web/components/layout/Sidebar.tsx
'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/cn';
import {
  Sun, MessageSquare, LayoutGrid, GitBranch,
  RotateCcw, Settings, Zap
} from 'lucide-react';

const NAV = [
  { href: '/today',    icon: Sun,           label: 'Today' },
  { href: '/chat',     icon: MessageSquare, label: 'Chat' },
  { href: '/domains',  icon: LayoutGrid,    label: 'Domains' },
  { href: '/graph',    icon: GitBranch,     label: 'Life Graph' },
  { href: '/replay',   icon: RotateCcw,     label: 'Replay' },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-14 lg:w-52 flex-shrink-0 flex flex-col h-full border-r border-[var(--v2-border)] bg-[var(--v2-sidebar)]">
      {/* Logo */}
      <div className="h-12 flex items-center px-4 border-b border-[var(--v2-border)]">
        <span className="hidden lg:flex items-center gap-2">
          <Zap size={16} className="text-[var(--v2-violet)]" />
          <span className="text-sm font-bold text-[var(--v2-text)] tracking-wider">CHIEF</span>
        </span>
        <Zap size={16} className="lg:hidden text-[var(--v2-violet)]" />
      </div>
      {/* Nav */}
      <nav className="flex-1 py-3 space-y-0.5 px-2">
        {NAV.map(({ href, icon: Icon, label }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 px-2 py-2 rounded-[10px] transition-all duration-100',
                'text-[13px] font-medium',
                active
                  ? 'bg-[rgba(138,58,255,0.12)] text-[var(--v2-text)] border border-[rgba(138,58,255,0.20)]'
                  : 'text-[var(--v2-muted)] hover:bg-[rgba(247,240,255,0.05)] hover:text-[var(--v2-text-dim)]'
              )}
            >
              <Icon size={15} />
              <span className="hidden lg:block">{label}</span>
            </Link>
          );
        })}
      </nav>
      {/* Settings */}
      <div className="p-2 border-t border-[var(--v2-border)]">
        <Link
          href="/settings"
          className={cn(
            'flex items-center gap-3 px-2 py-2 rounded-[10px] transition-all duration-100',
            'text-[13px] font-medium',
            pathname.startsWith('/settings')
              ? 'bg-[rgba(138,58,255,0.12)] text-[var(--v2-text)] border border-[rgba(138,58,255,0.20)]'
              : 'text-[var(--v2-muted)] hover:bg-[rgba(247,240,255,0.05)] hover:text-[var(--v2-text-dim)]'
          )}
        >
          <Settings size={15} />
          <span className="hidden lg:block">Settings</span>
        </Link>
      </div>
    </aside>
  );
}
```

- [ ] **Step 3: Create TopBar**

```tsx
// apps/web/components/layout/TopBar.tsx
'use client';
import { Bell } from 'lucide-react';
import { Button } from '@/components/design-system';
import { createClient } from '@/lib/supabase/client';
import { useRouter } from 'next/navigation';

interface TopBarProps {
  title: string;
  momentumScore?: number;
}

export function TopBar({ title, momentumScore }: TopBarProps) {
  const router = useRouter();
  const supabase = createClient();

  async function signOut() {
    await supabase.auth.signOut();
    router.push('/login');
  }

  return (
    <header className="h-12 flex items-center justify-between px-4 border-b border-[var(--v2-border)] bg-[rgba(8,10,14,0.80)] backdrop-blur-sm flex-shrink-0">
      <h1 className="text-sm font-semibold text-[var(--v2-text)]">{title}</h1>
      <div className="flex items-center gap-3">
        {momentumScore !== undefined && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[rgba(138,58,255,0.12)] border border-[rgba(138,58,255,0.20)]">
            <div className="w-1.5 h-1.5 rounded-full bg-[var(--v2-violet)]" />
            <span className="text-[12px] font-semibold text-[var(--v2-text)]">{momentumScore}</span>
            <span className="text-[11px] text-[var(--v2-muted)]">momentum</span>
          </div>
        )}
        <Button variant="ghost" size="xs" className="w-8 h-8 p-0 justify-center">
          <Bell size={14} />
        </Button>
        <Button variant="ghost" size="xs" onClick={signOut}>
          Sign out
        </Button>
      </div>
    </header>
  );
}
```

- [ ] **Step 4: Create app shell layout**

```tsx
// apps/web/app/(app)/layout.tsx
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { Sidebar } from '@/components/layout/Sidebar';

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect('/login');

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        {children}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Create root redirect**

```tsx
// apps/web/app/page.tsx
import { redirect } from 'next/navigation';
export default function RootPage() {
  redirect('/today');
}
```

- [ ] **Step 6: Move today/chat/settings into (app) route group**

Create the directory structure:
```
apps/web/app/(app)/today/page.tsx
apps/web/app/(app)/chat/page.tsx
apps/web/app/(app)/settings/page.tsx
```

Placeholder today page:
```tsx
// apps/web/app/(app)/today/page.tsx
import { TopBar } from '@/components/layout/TopBar';
export default function TodayPage() {
  return (
    <>
      <TopBar title="Today" momentumScore={71} />
      <main className="flex-1 overflow-y-auto p-4">
        <p className="text-[var(--v2-muted)] text-sm">Morning brief loading...</p>
      </main>
    </>
  );
}
```

Placeholder chat page:
```tsx
// apps/web/app/(app)/chat/page.tsx
import { TopBar } from '@/components/layout/TopBar';
export default function ChatPage() {
  return (
    <>
      <TopBar title="Chat" />
      <main className="flex-1 overflow-y-auto p-4">
        <p className="text-[var(--v2-muted)] text-sm">Chat loading...</p>
      </main>
    </>
  );
}
```

Placeholder settings page:
```tsx
// apps/web/app/(app)/settings/page.tsx
import { TopBar } from '@/components/layout/TopBar';
export default function SettingsPage() {
  return (
    <>
      <TopBar title="Settings" />
      <main className="flex-1 overflow-y-auto p-4">
        <p className="text-[var(--v2-muted)] text-sm">Settings loading...</p>
      </main>
    </>
  );
}
```

- [ ] **Step 7: Verify shell renders**

Run `npm run dev`. After logging in, navigate to /today — should see: left sidebar with nav icons, top bar with "Today" + momentum pill, main area with placeholder text.

- [ ] **Step 8: Commit**

```bash
cd C:/Users/Micha/chief
git add apps/web/
git commit -m "feat: add app shell with sidebar, top bar, and route structure"
```

---

## Task 7: Today view — Morning Brief, Momentum Score, Approval Queue components

**Files:**
- Create: `apps/web/components/today/MomentumScore.tsx`
- Create: `apps/web/components/today/MorningBrief.tsx`
- Create: `apps/web/components/today/ApprovalQueue.tsx`
- Modify: `apps/web/app/(app)/today/page.tsx`

- [ ] **Step 1: Create MomentumScore component**

```tsx
// apps/web/components/today/MomentumScore.tsx
'use client';
import { motion } from 'framer-motion';
import { cn } from '@/lib/cn';

interface DomainScore {
  label: string;
  value: number;
  color: string;
}

interface MomentumScoreProps {
  total: number;
  domains: DomainScore[];
}

export function MomentumScore({ total, domains }: MomentumScoreProps) {
  const circumference = 2 * Math.PI * 36;
  const progress = (total / 100) * circumference;

  return (
    <div className="flex items-center gap-6 p-5 rounded-[16px] border border-[rgba(247,240,255,0.10)] [background:linear-gradient(180deg,rgba(18,24,34,0.98),rgba(11,15,22,0.98))] shadow-[inset_0_1px_0_rgba(255,255,255,0.035),0_18px_55px_rgba(0,0,0,0.38)]">
      {/* Ring */}
      <div className="relative flex-shrink-0">
        <svg width="90" height="90" viewBox="0 0 90 90">
          <circle cx="45" cy="45" r="36" fill="none" stroke="rgba(247,240,255,0.07)" strokeWidth="6" />
          <motion.circle
            cx="45" cy="45" r="36"
            fill="none"
            stroke="url(#scoreGrad)"
            strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: circumference - progress }}
            transition={{ duration: 1.2, ease: [0.32, 0.72, 0, 1] }}
            transform="rotate(-90 45 45)"
          />
          <defs>
            <linearGradient id="scoreGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#2633D9" />
              <stop offset="100%" stopColor="#8A3AFF" />
            </linearGradient>
          </defs>
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-[22px] font-bold text-[var(--v2-text)]">{total}</span>
          <span className="text-[10px] text-[var(--v2-muted)] uppercase tracking-wider">momentum</span>
        </div>
      </div>
      {/* Domain bars */}
      <div className="flex-1 grid grid-cols-2 gap-x-6 gap-y-2">
        {domains.map(d => (
          <div key={d.label} className="space-y-1">
            <div className="flex justify-between items-center">
              <span className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-muted)]">{d.label}</span>
              <span className="text-[12px] font-semibold text-[var(--v2-text-dim)]">{d.value}</span>
            </div>
            <div className="h-1 rounded-full bg-[rgba(247,240,255,0.07)] overflow-hidden">
              <motion.div
                className="h-full rounded-full"
                style={{ background: d.color }}
                initial={{ width: 0 }}
                animate={{ width: `${d.value}%` }}
                transition={{ duration: 0.8, delay: 0.3, ease: [0.32, 0.72, 0, 1] }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create MorningBrief component**

```tsx
// apps/web/components/today/MorningBrief.tsx
import { Panel, StatusDot } from '@/components/design-system';
import { Activity, DollarSign, Briefcase, FileText } from 'lucide-react';

interface BriefSection {
  domain: 'body' | 'money' | 'work' | 'admin';
  agent: string;
  status: 'ok' | 'med' | 'high' | 'crit';
  headline: string;
  detail: string;
  action?: string;
}

interface MorningBriefProps {
  greeting: string;
  sections: BriefSection[];
}

const DOMAIN_ICONS = {
  body:  Activity,
  money: DollarSign,
  work:  Briefcase,
  admin: FileText,
};

const DOMAIN_LABELS = {
  body:  'Body',
  money: 'Money',
  work:  'Work',
  admin: 'Admin',
};

export function MorningBrief({ greeting, sections }: MorningBriefProps) {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-[var(--v2-text)]">{greeting}</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {sections.map(s => {
          const Icon = DOMAIN_ICONS[s.domain];
          return (
            <Panel key={s.domain} className="p-4 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Icon size={14} className="text-[var(--v2-violet)]" />
                  <span className="text-[11px] uppercase tracking-[0.08em] font-semibold text-[var(--v2-muted)]">
                    {DOMAIN_LABELS[s.domain]}
                  </span>
                  <span className="text-[10px] text-[var(--v2-subtle)]">[{s.agent}]</span>
                </div>
                <StatusDot severity={s.status} size="xs" />
              </div>
              <p className="text-sm font-medium text-[var(--v2-text)]">{s.headline}</p>
              <p className="text-[12px] text-[var(--v2-muted)]">{s.detail}</p>
              {s.action && (
                <p className="text-[12px] text-[var(--v2-violet)]">→ {s.action}</p>
              )}
            </Panel>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create ApprovalQueue component**

```tsx
// apps/web/components/today/ApprovalQueue.tsx
'use client';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Panel, Button, StatusDot } from '@/components/design-system';
import { CheckCircle, XCircle, ChevronDown } from 'lucide-react';

interface QueueItem {
  id: string;
  agent: string;
  title: string;
  description: string;
  riskLevel: 'auto' | 'notify' | 'approve' | 'confirm';
}

interface ApprovalQueueProps {
  items: QueueItem[];
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}

const RISK_COLORS: Record<QueueItem['riskLevel'], string> = {
  auto:    'ok',
  notify:  'info',
  approve: 'med',
  confirm: 'high',
};

export function ApprovalQueue({ items, onApprove, onReject }: ApprovalQueueProps) {
  const [expanded, setExpanded] = useState<string | null>(null);

  if (items.length === 0) return null;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-[12px] uppercase tracking-[0.08em] font-semibold text-[var(--v2-muted)]">
          Queue — {items.length} item{items.length !== 1 ? 's' : ''}
        </h3>
      </div>
      <AnimatePresence initial={false}>
        {items.map(item => (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, x: 40, transition: { duration: 0.2 } }}
            transition={{ duration: 0.25 }}
          >
            <Panel className="p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-2 flex-1 min-w-0">
                  <StatusDot severity={RISK_COLORS[item.riskLevel] as any} size="xs" className="mt-1 flex-shrink-0" />
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-[var(--v2-text)] truncate">{item.title}</span>
                      <span className="text-[10px] text-[var(--v2-subtle)] flex-shrink-0">[{item.agent}]</span>
                    </div>
                    {expanded === item.id && (
                      <p className="text-[12px] text-[var(--v2-muted)] mt-1">{item.description}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  <Button
                    variant="ghost"
                    size="xs"
                    onClick={() => setExpanded(expanded === item.id ? null : item.id)}
                  >
                    <ChevronDown size={12} className={expanded === item.id ? 'rotate-180 transition-transform' : 'transition-transform'} />
                  </Button>
                  <Button variant="ghost" size="xs" onClick={() => onReject(item.id)}>
                    <XCircle size={13} className="text-[var(--v2-crit)]" />
                  </Button>
                  <Button variant="solid" size="xs" onClick={() => onApprove(item.id)}>
                    <CheckCircle size={13} />
                    Approve
                  </Button>
                </div>
              </div>
            </Panel>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
```

- [ ] **Step 4: Wire up Today page with stub data**

```tsx
// apps/web/app/(app)/today/page.tsx
import { TopBar } from '@/components/layout/TopBar';
import { MomentumScore } from '@/components/today/MomentumScore';
import { MorningBrief } from '@/components/today/MorningBrief';
import { ApprovalQueueClient } from '@/components/today/ApprovalQueueClient';

const STUB_DOMAINS = [
  { label: 'Body',       value: 74, color: '#18E6D8' },
  { label: 'Money',      value: 62, color: '#F7A93B' },
  { label: 'Work',       value: 69, color: '#8A3AFF' },
  { label: 'Admin',      value: 80, color: '#38F2A8' },
  { label: 'Discipline', value: 71, color: '#3B82F6' },
];

const STUB_BRIEF = [
  {
    domain: 'body' as const,
    agent: 'Pulse',
    status: 'med' as const,
    headline: 'Recovery 72% · Sleep 6h 20m',
    detail: 'Slightly below target. Skip heavy compounds today.',
    action: 'Upper accessories recommended',
  },
  {
    domain: 'money' as const,
    agent: 'Ledger',
    status: 'high' as const,
    headline: '€92 over weekly spend target',
    detail: 'Biggest category: eating out (€64). Two unused subscriptions detected.',
    action: 'Review subscription waste',
  },
  {
    domain: 'work' as const,
    agent: 'Forge + Echo',
    status: 'med' as const,
    headline: 'Professor email 5 days stale',
    detail: 'Thesis code progress strong, written output lagging.',
    action: 'Send progress update today',
  },
  {
    domain: 'admin' as const,
    agent: 'Clerk',
    status: 'ok' as const,
    headline: 'Insurance reply due in 6 days',
    detail: 'Draft is ready and waiting for your approval.',
    action: 'Draft ready — approve below',
  },
];

export default function TodayPage() {
  const hour = new Date().getHours();
  const greeting =
    hour < 12 ? 'Good morning, Mohamed.' :
    hour < 18 ? 'Good afternoon, Mohamed.' :
                'Good evening, Mohamed.';

  return (
    <>
      <TopBar title="Today" momentumScore={71} />
      <main className="flex-1 overflow-y-auto p-4 space-y-5 max-w-3xl">
        <MomentumScore total={71} domains={STUB_DOMAINS} />
        <MorningBrief greeting={greeting} sections={STUB_BRIEF} />
        <ApprovalQueueClient />
      </main>
    </>
  );
}
```

- [ ] **Step 5: Create ApprovalQueueClient wrapper (client component for interactivity)**

```tsx
// apps/web/components/today/ApprovalQueueClient.tsx
'use client';
import { useState } from 'react';
import { ApprovalQueue } from './ApprovalQueue';
import { toast } from 'sonner';

const STUB_QUEUE = [
  {
    id: '1',
    agent: 'Echo',
    title: 'Professor email draft ready',
    description: 'Progress update on evaluation setup. Mentions completed training script, pending results table.',
    riskLevel: 'approve' as const,
  },
  {
    id: '2',
    agent: 'Ledger',
    title: 'Cancel Audible subscription',
    description: 'No activity detected in 62 days. Monthly cost: €9.95.',
    riskLevel: 'confirm' as const,
  },
];

export function ApprovalQueueClient() {
  const [items, setItems] = useState(STUB_QUEUE);

  function handleApprove(id: string) {
    const item = items.find(i => i.id === id);
    setItems(prev => prev.filter(i => i.id !== id));
    toast.success(`Approved: ${item?.title}`);
  }

  function handleReject(id: string) {
    const item = items.find(i => i.id === id);
    setItems(prev => prev.filter(i => i.id !== id));
    toast(`Skipped: ${item?.title}`);
  }

  return (
    <ApprovalQueue
      items={items}
      onApprove={handleApprove}
      onReject={handleReject}
    />
  );
}
```

- [ ] **Step 6: Verify Today page renders**

Run `npm run dev`. Navigate to /today. Should see:
- Animated momentum ring (71/100) with 5 domain progress bars
- 4 morning brief cards (Body, Money, Work, Admin)
- 2 approval queue items with Approve/Skip buttons

- [ ] **Step 7: Commit**

```bash
cd C:/Users/Micha/chief
git add apps/web/
git commit -m "feat: add Today view with MomentumScore, MorningBrief, ApprovalQueue"
```

---

## Task 8: Chat view with message UI

**Files:**
- Create: `apps/web/store/chat.ts`
- Create: `apps/web/components/chat/Message.tsx`
- Create: `apps/web/components/chat/ChatInput.tsx`
- Create: `apps/web/components/chat/ChatPanel.tsx`
- Modify: `apps/web/app/(app)/chat/page.tsx`
- Create: `apps/web/app/api/chat/route.ts`

- [ ] **Step 1: Create chat store**

```ts
// apps/web/store/chat.ts
import { create } from 'zustand';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  agent?: string;
  createdAt: Date;
}

interface ChatStore {
  messages: ChatMessage[];
  isLoading: boolean;
  addMessage: (msg: Omit<ChatMessage, 'id' | 'createdAt'>) => void;
  setLoading: (loading: boolean) => void;
  clear: () => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  isLoading: false,
  addMessage: (msg) =>
    set(s => ({
      messages: [
        ...s.messages,
        { ...msg, id: crypto.randomUUID(), createdAt: new Date() },
      ],
    })),
  setLoading: (isLoading) => set({ isLoading }),
  clear: () => set({ messages: [] }),
}));
```

- [ ] **Step 2: Create Message component**

```tsx
// apps/web/components/chat/Message.tsx
import { cn } from '@/lib/cn';
import type { ChatMessage } from '@/store/chat';

interface MessageProps {
  message: ChatMessage;
}

export function Message({ message }: MessageProps) {
  const isUser = message.role === 'user';
  return (
    <div className={cn('flex gap-3', isUser && 'justify-end')}>
      {!isUser && (
        <div className="w-7 h-7 rounded-full bg-[linear-gradient(135deg,#2633D9,#8A3AFF)] flex-shrink-0 flex items-center justify-center mt-0.5">
          <span className="text-[10px] font-bold text-white">C</span>
        </div>
      )}
      <div
        className={cn(
          'max-w-[75%] px-3.5 py-2.5 rounded-[14px] text-sm',
          isUser
            ? 'bg-[rgba(138,58,255,0.15)] border border-[rgba(138,58,255,0.25)] text-[var(--v2-text)] rounded-tr-[4px]'
            : 'border border-[rgba(247,240,255,0.10)] [background:linear-gradient(180deg,rgba(18,24,34,0.98),rgba(11,15,22,0.98))] text-[var(--v2-text-dim)] rounded-tl-[4px]'
        )}
      >
        {!isUser && message.agent && (
          <div className="text-[10px] text-[var(--v2-violet)] uppercase tracking-[0.08em] mb-1">
            via {message.agent}
          </div>
        )}
        <p className="leading-relaxed whitespace-pre-wrap">{message.content}</p>
        <div className="text-[10px] text-[var(--v2-subtle)] mt-1.5">
          {message.createdAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create ChatInput component**

```tsx
// apps/web/components/chat/ChatInput.tsx
'use client';
import { useState, useRef, type KeyboardEvent } from 'react';
import { Button } from '@/components/design-system';
import { SendHorizontal } from 'lucide-react';

interface ChatInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function submit() {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function handleInput(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setValue(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  }

  return (
    <div className="p-3 border-t border-[var(--v2-border)]">
      <div className="flex items-end gap-2 bg-[rgba(247,240,255,0.04)] border border-[rgba(247,240,255,0.12)] rounded-[14px] px-3 py-2 focus-within:border-[var(--v2-border-focus)] transition-colors">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Ask Chief anything..."
          rows={1}
          disabled={disabled}
          className="flex-1 bg-transparent text-sm text-[var(--v2-text)] placeholder:text-[var(--v2-subtle)] resize-none outline-none leading-relaxed"
          style={{ minHeight: '24px', maxHeight: '160px' }}
        />
        <Button
          variant="solid"
          size="xs"
          onClick={submit}
          disabled={!value.trim() || disabled}
          className="flex-shrink-0 mb-0.5"
        >
          <SendHorizontal size={12} />
        </Button>
      </div>
      <p className="text-[10px] text-[var(--v2-subtle)] mt-1.5 px-1">Enter to send · Shift+Enter for newline</p>
    </div>
  );
}
```

- [ ] **Step 4: Create ChatPanel component**

```tsx
// apps/web/components/chat/ChatPanel.tsx
'use client';
import { useEffect, useRef } from 'react';
import { Message } from './Message';
import { ChatInput } from './ChatInput';
import { useChatStore } from '@/store/chat';

export function ChatPanel() {
  const { messages, isLoading, addMessage, setLoading } = useChatStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function handleSend(content: string) {
    addMessage({ role: 'user', content });
    setLoading(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content, history: messages.slice(-10) }),
      });
      const data = await res.json();
      addMessage({ role: 'assistant', content: data.reply, agent: data.agent });
    } catch {
      addMessage({ role: 'assistant', content: "I'm having trouble connecting right now. Try again in a moment." });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-3 pb-12">
            <div className="w-12 h-12 rounded-full bg-[linear-gradient(135deg,#2633D9,#8A3AFF)] flex items-center justify-center">
              <span className="text-lg font-bold text-white">C</span>
            </div>
            <div>
              <p className="text-sm font-medium text-[var(--v2-text)]">Hey, I'm Chief.</p>
              <p className="text-[13px] text-[var(--v2-muted)] mt-1">Ask me anything about your health, finances, work, or admin.</p>
            </div>
          </div>
        )}
        {messages.map(msg => <Message key={msg.id} message={msg} />)}
        {isLoading && (
          <div className="flex gap-3">
            <div className="w-7 h-7 rounded-full bg-[linear-gradient(135deg,#2633D9,#8A3AFF)] flex-shrink-0 flex items-center justify-center">
              <span className="text-[10px] font-bold text-white">C</span>
            </div>
            <div className="px-3.5 py-2.5 rounded-[14px] rounded-tl-[4px] border border-[rgba(247,240,255,0.10)] [background:linear-gradient(180deg,rgba(18,24,34,0.98),rgba(11,15,22,0.98))]">
              <div className="flex gap-1 items-center h-5">
                {[0, 0.15, 0.3].map(delay => (
                  <div
                    key={delay}
                    className="w-1.5 h-1.5 rounded-full bg-[var(--v2-violet)]"
                    style={{ animation: `chief-pulse 1.2s ease-in-out ${delay}s infinite` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <ChatInput onSend={handleSend} disabled={isLoading} />
    </div>
  );
}
```

- [ ] **Step 5: Create Next.js API chat route (gateway to Python service)**

```ts
// apps/web/app/api/chat/route.ts
import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  const body = await request.json();
  const agentServiceUrl = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8001';

  try {
    const res = await fetch(`${agentServiceUrl}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    // Python service not running yet — return stub
    return NextResponse.json({
      reply: "Hey — I'm Chief. I'm still getting set up, but I'm here. What's on your mind?",
      agent: 'Chief',
    });
  }
}
```

- [ ] **Step 6: Wire up Chat page**

```tsx
// apps/web/app/(app)/chat/page.tsx
import { TopBar } from '@/components/layout/TopBar';
import { ChatPanel } from '@/components/chat/ChatPanel';

export default function ChatPage() {
  return (
    <>
      <TopBar title="Chat" />
      <div className="flex-1 overflow-hidden">
        <ChatPanel />
      </div>
    </>
  );
}
```

- [ ] **Step 7: Verify chat renders**

Navigate to /chat. Should see: Chief avatar + intro message. Type a message + send. Should get the stub reply "Hey — I'm Chief. I'm still getting set up...". Typing indicator (3 pulsing dots) should show while loading.

- [ ] **Step 8: Commit**

```bash
cd C:/Users/Micha/chief
git add apps/web/
git commit -m "feat: add Chat view with message UI and API gateway route"
```

---

## Task 9: Python FastAPI agent service

**Files:**
- Create: `services/agents/main.py`
- Create: `services/agents/models.py`
- Create: `services/agents/orchestrator.py`
- Create: `services/agents/agents/__init__.py`
- Create: `services/agents/agents/base.py`
- Create: `services/agents/agents/pulse.py`
- Create: `services/agents/agents/echo.py`
- Create: `services/agents/agents/forge.py`
- Create: `services/agents/requirements.txt`
- Create: `services/agents/.env.example`

- [ ] **Step 1: Create requirements.txt**

```
# services/agents/requirements.txt
fastapi==0.115.5
uvicorn[standard]==0.32.1
pydantic==2.10.3
anthropic==0.39.0
python-dotenv==1.0.1
httpx==0.28.1
```

- [ ] **Step 2: Create Pydantic models**

```python
# services/agents/models.py
from pydantic import BaseModel
from typing import Optional

class ChatMessage(BaseModel):
    role: str  # 'user' | 'assistant'
    content: str
    agent: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    agent: str
    confidence: Optional[str] = None
```

- [ ] **Step 3: Create BaseAgent**

```python
# services/agents/agents/base.py
from abc import ABC, abstractmethod
from models import ChatRequest, ChatResponse

class BaseAgent(ABC):
    name: str
    description: str

    @abstractmethod
    async def handle(self, request: ChatRequest) -> ChatResponse:
        """Handle a routed message. Return a ChatResponse."""
        ...
```

- [ ] **Step 4: Create stub agents**

```python
# services/agents/agents/__init__.py
from .pulse import PulseAgent
from .echo import EchoAgent
from .forge import ForgeAgent

__all__ = ['PulseAgent', 'EchoAgent', 'ForgeAgent']
```

```python
# services/agents/agents/pulse.py
from agents.base import BaseAgent
from models import ChatRequest, ChatResponse
import anthropic, os

class PulseAgent(BaseAgent):
    name = 'Pulse'
    description = 'Health and fitness domain: recovery, sleep, gym planning, nutrition, weight.'

    async def handle(self, request: ChatRequest) -> ChatResponse:
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        messages = [{'role': m.role, 'content': m.content} for m in request.history]
        messages.append({'role': 'user', 'content': request.message})

        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=512,
            system=(
                "You are Pulse, Chief's health and fitness agent. "
                "You're warm, direct, and knowledgeable about recovery, training, and nutrition. "
                "You speak like a mentor who knows the user's body well. "
                "Keep responses concise — 2-4 sentences unless detail is needed. "
                "Always be honest about confidence levels (e.g. 'estimated', 'based on limited data')."
            ),
            messages=messages,
        )
        return ChatResponse(reply=response.content[0].text, agent='Pulse')
```

```python
# services/agents/agents/echo.py
from agents.base import BaseAgent
from models import ChatRequest, ChatResponse
import anthropic, os

class EchoAgent(BaseAgent):
    name = 'Echo'
    description = 'Communication domain: emails, replies, thread summarization, follow-ups, tone.'

    async def handle(self, request: ChatRequest) -> ChatResponse:
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        messages = [{'role': m.role, 'content': m.content} for m in request.history]
        messages.append({'role': 'user', 'content': request.message})

        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=1024,
            system=(
                "You are Echo, Chief's communication agent. "
                "You help draft emails, summarize threads, and manage communication tasks. "
                "Match the user's tone — if they write casually, be casual; if formally, be formal. "
                "When drafting emails, always show a preview and ask for approval before sending anything."
            ),
            messages=messages,
        )
        return ChatResponse(reply=response.content[0].text, agent='Echo')
```

```python
# services/agents/agents/forge.py
from agents.base import BaseAgent
from models import ChatRequest, ChatResponse
import anthropic, os

class ForgeAgent(BaseAgent):
    name = 'Forge'
    description = 'Projects domain: thesis, GitHub repos, startup tasks, Notion, deliverables, velocity.'

    async def handle(self, request: ChatRequest) -> ChatResponse:
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        messages = [{'role': m.role, 'content': m.content} for m in request.history]
        messages.append({'role': 'user', 'content': request.message})

        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=512,
            system=(
                "You are Forge, Chief's projects and work agent. "
                "You track progress, identify blockers, and help prioritize work. "
                "Be direct about what the most valuable next action is. "
                "Reference concrete data (commits, deadlines, task counts) when available."
            ),
            messages=messages,
        )
        return ChatResponse(reply=response.content[0].text, agent='Forge')
```

- [ ] **Step 5: Create orchestrator**

```python
# services/agents/orchestrator.py
import anthropic, os
from models import ChatRequest, ChatResponse
from agents import PulseAgent, EchoAgent, ForgeAgent

AGENTS = [PulseAgent(), EchoAgent(), ForgeAgent()]

ROUTING_SYSTEM = """You are Chief's routing intelligence. Given a user message, decide which specialist to use.

Specialists:
- Pulse: health, fitness, sleep, recovery, gym, nutrition, food, weight, injury
- Echo: emails, communication, professor, reply, draft, message, thread, follow-up
- Forge: thesis, GitHub, code, project, task, startup, deadline, commit, work
- Chief: anything else, general questions, cross-domain, strategy, planning

Respond with ONLY the specialist name (Pulse, Echo, Forge, or Chief). Nothing else."""

async def route_and_handle(request: ChatRequest) -> ChatResponse:
    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    # Route to specialist
    routing_response = client.messages.create(
        model='claude-haiku-4-5-20251001',  # cheap for routing
        max_tokens=10,
        system=ROUTING_SYSTEM,
        messages=[{'role': 'user', 'content': request.message}],
    )
    agent_name = routing_response.content[0].text.strip()

    # Find matching agent
    agent = next((a for a in AGENTS if a.name == agent_name), None)

    if agent:
        return await agent.handle(request)

    # Chief handles it directly
    chief_response = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=1024,
        system=(
            "You are Chief, a personal life operating system. "
            "You're a trusted advisor — warm, direct, and intelligent. "
            "You know the user's health, finances, work, and admin. "
            "For now you don't have real data connected yet, but be helpful about what you can do. "
            "Keep responses concise and actionable. "
            "Never say 'As an AI' — just be Chief."
        ),
        messages=[{'role': m.role, 'content': m.content} for m in request.history] +
                 [{'role': 'user', 'content': request.message}],
    )
    return ChatResponse(reply=chief_response.content[0].text, agent='Chief')
```

- [ ] **Step 6: Create FastAPI main app**

```python
# services/agents/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from models import ChatRequest, ChatResponse
from orchestrator import route_and_handle

load_dotenv()

app = FastAPI(title='Chief Agent Service', version='0.1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000', 'https://chief.app'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'chief-agents'}

@app.post('/chat', response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    return await route_and_handle(request)
```

- [ ] **Step 7: Create .env.example for agents**

```bash
cat > services/agents/.env.example << 'EOF'
ANTHROPIC_API_KEY=sk-ant-...
EOF
cp services/agents/.env.example services/agents/.env
# Then add your actual API key to services/agents/.env
```

- [ ] **Step 8: Create and activate Python venv, install deps**

```bash
cd C:/Users/Micha/chief/services/agents
python -m venv .venv
source .venv/Scripts/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

- [ ] **Step 9: Verify agent service starts**

```bash
uvicorn main:app --reload --port 8001
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8001
INFO:     Application startup complete.
```

Open http://localhost:8001/health — should return `{"status":"ok","service":"chief-agents"}`.

- [ ] **Step 10: Test routing end-to-end**

With both services running (`npm run dev:web` and `uvicorn`), go to /chat and send:
- "What should I train today?" → reply should say `via Pulse`
- "Can you draft an email to my professor?" → reply should say `via Echo`
- "What's the status of my thesis?" → reply should say `via Forge`
- "What is Chief?" → reply should say `via Chief`

- [ ] **Step 11: Commit**

```bash
cd C:/Users/Micha/chief
git add services/agents/
git commit -m "feat: add Python FastAPI agent service with Chief orchestrator and Pulse/Echo/Forge stubs"
```

---

## Task 10: Settings page with connector placeholders

**Files:**
- Modify: `apps/web/app/(app)/settings/page.tsx`

- [ ] **Step 1: Build settings page with connector status cards**

```tsx
// apps/web/app/(app)/settings/page.tsx
import { TopBar } from '@/components/layout/TopBar';
import { Panel, Button, StatusDot } from '@/components/design-system';
import { Mail, Calendar, Github, Activity, CreditCard } from 'lucide-react';

const CONNECTORS = [
  {
    id: 'gmail',
    name: 'Gmail',
    description: 'Email threads, subscriptions, receipts, contacts',
    icon: Mail,
    status: 'disconnected' as const,
    phase: 1,
  },
  {
    id: 'calendar',
    name: 'Google Calendar',
    description: 'Schedule, availability, deadlines',
    icon: Calendar,
    status: 'disconnected' as const,
    phase: 1,
  },
  {
    id: 'github',
    name: 'GitHub',
    description: 'Repos, commits, activity, PRs',
    icon: Github,
    status: 'disconnected' as const,
    phase: 1,
  },
  {
    id: 'whoop',
    name: 'WHOOP',
    description: 'Sleep, recovery, strain, HRV',
    icon: Activity,
    status: 'disconnected' as const,
    phase: 1,
  },
  {
    id: 'banking',
    name: 'Open Banking',
    description: 'Transactions, balances, recurring payments (via Tink)',
    icon: CreditCard,
    status: 'coming_soon' as const,
    phase: 2,
  },
];

const STATUS_MAP = {
  connected:    { label: 'Connected',   severity: 'ok' as const },
  disconnected: { label: 'Connect',     severity: 'low' as const },
  coming_soon:  { label: 'Coming soon', severity: 'info' as const },
};

export default function SettingsPage() {
  return (
    <>
      <TopBar title="Settings" />
      <main className="flex-1 overflow-y-auto p-4 max-w-2xl space-y-6">
        <section className="space-y-3">
          <div>
            <h2 className="text-sm font-semibold text-[var(--v2-text)]">Connectors</h2>
            <p className="text-[12px] text-[var(--v2-muted)] mt-0.5">
              Connect your sources. Chief builds your Life Graph from these.
            </p>
          </div>
          <div className="space-y-2">
            {CONNECTORS.map(c => {
              const status = STATUS_MAP[c.status];
              const Icon = c.icon;
              return (
                <Panel key={c.id} className="p-4 flex items-center gap-4">
                  <div className="w-8 h-8 rounded-[10px] bg-[rgba(138,58,255,0.12)] border border-[rgba(138,58,255,0.20)] flex items-center justify-center flex-shrink-0">
                    <Icon size={15} className="text-[var(--v2-violet)]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-[var(--v2-text)]">{c.name}</span>
                      <span className="text-[10px] text-[var(--v2-subtle)]">Phase {c.phase}</span>
                    </div>
                    <p className="text-[12px] text-[var(--v2-muted)] truncate">{c.description}</p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <StatusDot severity={status.severity} size="xs" />
                    <Button
                      variant={c.status === 'connected' ? 'outline' : 'ghost'}
                      size="xs"
                      disabled={c.status === 'coming_soon'}
                    >
                      {status.label}
                    </Button>
                  </div>
                </Panel>
              );
            })}
          </div>
        </section>
      </main>
    </>
  );
}
```

- [ ] **Step 2: Verify settings page renders**

Navigate to /settings. Should see 5 connector cards with icons, descriptions, phase badges, and Connect/Coming soon buttons.

- [ ] **Step 3: Commit**

```bash
cd C:/Users/Micha/chief
git add apps/web/
git commit -m "feat: add Settings page with connector status cards"
```

---

## Self-Review

**Spec coverage check:**
- ✅ Project scaffold in monorepo structure (apps/web + services/agents)
- ✅ Auth flow (Supabase magic link + middleware)
- ✅ Life Graph schema (all 9 entity types as SQL tables with RLS)
- ✅ Base UI shell (sidebar + top bar)
- ✅ Today view (MomentumScore + MorningBrief + ApprovalQueue)
- ✅ Chat view (ChatPanel + Message + ChatInput + API gateway)
- ✅ Settings view (connector status cards)
- ✅ Python agent service (FastAPI + Chief orchestrator + 3 stub agents)
- ✅ Lumina V2 design system ported (tokens + Button + Panel + StatusDot)

**Placeholder scan:** No TBDs, TODOs, or vague steps. All code blocks are complete. Commands have expected outputs.

**Type consistency check:**
- `ChatMessage` interface in `store/chat.ts` matches usage in `ChatPanel.tsx` ✅
- `BriefSection['domain']` in `MorningBrief.tsx` matches `DOMAIN_ICONS` and `DOMAIN_LABELS` maps ✅
- `QueueItem['riskLevel']` in `ApprovalQueue.tsx` matches `RISK_COLORS` map ✅
- `ChatRequest`/`ChatResponse` Pydantic models match `orchestrator.py` usage ✅
- `BaseAgent.handle()` signature matches all three agent implementations ✅

---

## Execution Options

Plan complete and saved to `docs/superpowers/plans/2026-05-26-chief-phase0-foundation.md`.

**Two execution options:**

**1. Subagent-Driven (recommended)** — Fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans with checkpoints

Which approach?
