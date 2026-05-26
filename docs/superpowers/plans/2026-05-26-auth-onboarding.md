# Auth + Onboarding Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the bare magic-link form with a premium branded login screen and add a 3-step onboarding wizard (name + timezone → role → focus goals) that runs once after first login.

**Architecture:** Login page splits into a brand panel (left) and auth card (right). The callback route checks whether a profile exists — new users land on `/onboarding`, returning users land on `/today`. The onboarding wizard lives in `app/(app)/onboarding/` with its own full-screen layout (no sidebar/topbar). On completion it POSTs to `/api/onboarding/complete` which writes to `profiles` and `lg_goals`, then redirects to `/today`.

**Tech Stack:** Next.js 15 App Router, Supabase JS v2, Framer Motion 12, Tailwind v4, Chief design system (Button/Panel/StatusDot/tokens.css), Lucide React icons.

---

## File Map

```
apps/web/
├── app/
│   ├── (auth)/
│   │   ├── login/page.tsx                    REPLACE — split-panel branded login
│   │   └── callback/route.ts                 MODIFY — check profile, redirect to /onboarding if new
│   ├── (app)/
│   │   └── onboarding/
│   │       ├── layout.tsx                    CREATE — full-screen, no Sidebar/TopBar
│   │       └── page.tsx                      CREATE — 3-step wizard client component
│   └── api/
│       └── onboarding/
│           └── complete/route.ts             CREATE — writes profiles + lg_goals, returns redirect
├── components/
│   └── onboarding/
│       ├── StepIndicator.tsx                 CREATE — 3 dots, active one filled violet
│       ├── RoleCard.tsx                      CREATE — selectable card with icon + label
│       └── FocusTagInput.tsx                 CREATE — chip input, max 3 tags, role-based suggestions
└── middleware.ts                             MODIFY — add /onboarding to protected paths
```

---

## Task 1: Premium login page

**Files:**
- Modify: `apps/web/app/(auth)/login/page.tsx`

- [ ] **Step 1: Replace login/page.tsx**

```tsx
// apps/web/app/(auth)/login/page.tsx
'use client';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { createClient } from '@/lib/supabase/client';
import { Button } from '@/components/design-system';
import { Zap, CheckCircle, Mail } from 'lucide-react';

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
    <div className="min-h-screen flex flex-col lg:flex-row">
      {/* Left: brand panel — hidden on mobile, full half on desktop */}
      <div className="hidden lg:flex flex-col justify-between w-1/2 min-h-screen p-12 relative overflow-hidden"
        style={{ background: 'radial-gradient(ellipse at 20% 10%, rgba(38,99,235,0.12), transparent 55%), radial-gradient(ellipse at 80% 80%, rgba(138,58,255,0.10), transparent 50%), #08090D' }}>
        {/* Ambient glow */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-0 left-0 w-96 h-96 rounded-full opacity-[0.04]"
            style={{ background: 'radial-gradient(circle, #8A3AFF, transparent)', transform: 'translate(-30%, -30%)' }} />
          <div className="absolute bottom-0 right-0 w-80 h-80 rounded-full opacity-[0.03]"
            style={{ background: 'radial-gradient(circle, #18E6D8, transparent)', transform: 'translate(30%, 30%)' }} />
        </div>
        {/* Logo */}
        <div className="flex items-center gap-2.5 relative z-10">
          <div className="w-8 h-8 rounded-full bg-[linear-gradient(135deg,#2633D9,#8A3AFF)] flex items-center justify-center">
            <Zap size={16} className="text-white" />
          </div>
          <span className="text-sm font-bold tracking-[0.12em] text-[var(--v2-text)] uppercase">Chief</span>
        </div>
        {/* Headline */}
        <div className="relative z-10 space-y-6">
          <div className="space-y-3">
            <h1 className="text-[3.5rem] font-bold leading-[1.05] text-[var(--v2-text)] tracking-tight">
              Your life,<br />
              <span className="text-transparent bg-clip-text bg-[linear-gradient(135deg,#8A3AFF,#2563EB)]">
                under management.
              </span>
            </h1>
            <p className="text-[var(--v2-muted)] text-lg leading-relaxed max-w-sm">
              One intelligence layer for your health, finances, work, communication, and admin.
            </p>
          </div>
          {/* Social proof row */}
          <div className="flex items-center gap-3">
            <div className="flex -space-x-2">
              {['#8A3AFF', '#18E6D8', '#F7A93B'].map((color, i) => (
                <div key={i} className="w-7 h-7 rounded-full border-2 border-[#08090D]"
                  style={{ background: color, opacity: 0.7 }} />
              ))}
            </div>
            <span className="text-[12px] text-[var(--v2-subtle)]">Used by founders, students &amp; builders</span>
          </div>
        </div>
        {/* Bottom attribution */}
        <p className="text-[11px] text-[var(--v2-subtle)] relative z-10">
          © 2026 Chief · Your data stays private
        </p>
      </div>

      {/* Mobile header (shown only on small screens) */}
      <div className="lg:hidden flex items-center gap-2.5 p-6 border-b border-[var(--v2-border)]">
        <div className="w-7 h-7 rounded-full bg-[linear-gradient(135deg,#2633D9,#8A3AFF)] flex items-center justify-center">
          <Zap size={14} className="text-white" />
        </div>
        <span className="text-sm font-bold tracking-[0.12em] text-[var(--v2-text)] uppercase">Chief</span>
      </div>

      {/* Right: auth card */}
      <div className="flex-1 flex items-center justify-center px-6 py-12 lg:px-16">
        <div className="w-full max-w-sm">
          <AnimatePresence mode="wait">
            {!sent ? (
              <motion.div
                key="form"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.25 }}
                className="space-y-7"
              >
                <div className="space-y-2">
                  <h2 className="text-2xl font-bold text-[var(--v2-text)]">Sign in</h2>
                  <p className="text-[var(--v2-muted)] text-sm">
                    Enter your email and we'll send a magic link.
                  </p>
                </div>
                <form onSubmit={handleMagicLink} className="space-y-3">
                  <div className="space-y-1.5">
                    <label className="text-[12px] font-medium text-[var(--v2-muted)] uppercase tracking-[0.08em]">
                      Email
                    </label>
                    <input
                      type="email"
                      placeholder="you@example.com"
                      value={email}
                      onChange={e => setEmail(e.target.value)}
                      required
                      autoFocus
                      className="w-full h-11 px-3.5 rounded-[10px] bg-[rgba(247,240,255,0.04)] border border-[rgba(247,240,255,0.12)] text-[var(--v2-text)] placeholder:text-[var(--v2-subtle)] text-sm focus:outline-none focus:border-[var(--v2-border-focus)] transition-colors"
                    />
                  </div>
                  <Button variant="solid" size="lg" className="w-full h-11" loading={loading} type="submit">
                    <Mail size={15} />
                    Send magic link
                  </Button>
                </form>
                <p className="text-[11px] text-[var(--v2-subtle)] text-center leading-relaxed">
                  By signing in you agree to our terms. No password needed.
                </p>
              </motion.div>
            ) : (
              <motion.div
                key="sent"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className="space-y-5 text-center"
              >
                <div className="flex justify-center">
                  <motion.div
                    initial={{ scale: 0.5, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ delay: 0.1, type: 'spring', stiffness: 200, damping: 18 }}
                    className="w-16 h-16 rounded-full bg-[rgba(56,242,168,0.10)] border border-[rgba(56,242,168,0.20)] flex items-center justify-center"
                  >
                    <CheckCircle size={28} className="text-[var(--v2-ok)]" />
                  </motion.div>
                </div>
                <div className="space-y-2">
                  <h2 className="text-xl font-bold text-[var(--v2-text)]">Check your email</h2>
                  <p className="text-[var(--v2-muted)] text-sm leading-relaxed">
                    We sent a magic link to<br />
                    <strong className="text-[var(--v2-text)]">{email}</strong>
                  </p>
                </div>
                <p className="text-[12px] text-[var(--v2-subtle)]">
                  The link expires in 1 hour.{' '}
                  <button
                    onClick={() => setSent(false)}
                    className="text-[var(--v2-violet)] hover:underline"
                  >
                    Use a different email
                  </button>
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: TypeScript check**

```bash
cd C:/Users/Micha/chief/apps/web && npx tsc --noEmit 2>&1 | grep "error TS" | head -5
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git -C C:/Users/Micha/chief add apps/web/app/\(auth\)/login/
git -C C:/Users/Micha/chief commit -m "feat: premium split-panel login page with brand panel and Framer Motion transitions"
git -C C:/Users/Micha/chief push
```

---

## Task 2: Update callback to detect new vs returning user

**Files:**
- Modify: `apps/web/app/(auth)/callback/route.ts`

- [ ] **Step 1: Replace callback/route.ts**

```ts
// apps/web/app/(auth)/callback/route.ts
import { createClient } from '@/lib/supabase/server';
import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get('code');

  if (!code) {
    return NextResponse.redirect(`${origin}/login`);
  }

  const supabase = await createClient();
  await supabase.auth.exchangeCodeForSession(code);

  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.redirect(`${origin}/login`);
  }

  // Check if this user has completed onboarding (has a display_name)
  const { data: profile } = await supabase
    .from('profiles')
    .select('display_name')
    .eq('id', user.id)
    .maybeSingle();

  const isNewUser = !profile || !profile.display_name;
  return NextResponse.redirect(`${origin}${isNewUser ? '/onboarding' : '/today'}`);
}
```

- [ ] **Step 2: TypeScript check**

```bash
cd C:/Users/Micha/chief/apps/web && npx tsc --noEmit 2>&1 | grep "error TS" | head -5
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git -C C:/Users/Micha/chief add apps/web/app/\(auth\)/callback/
git -C C:/Users/Micha/chief commit -m "feat: callback redirects new users to /onboarding, returning users to /today"
git -C C:/Users/Micha/chief push
```

---

## Task 3: Middleware — protect /onboarding

**Files:**
- Modify: `apps/web/middleware.ts`

- [ ] **Step 1: Add /onboarding to protected paths**

In `apps/web/middleware.ts`, find `const protectedPaths = [...]` and add `'/onboarding'`:

```ts
  const protectedPaths = ['/today', '/chat', '/settings', '/domains', '/graph', '/replay', '/onboarding'];
```

Also update the `config.matcher` array to include `/onboarding`:

```ts
export const config = {
  matcher: [
    '/today/:path*',
    '/chat/:path*',
    '/settings/:path*',
    '/domains/:path*',
    '/graph/:path*',
    '/replay/:path*',
    '/onboarding/:path*',
  ],
};
```

- [ ] **Step 2: Commit**

```bash
git -C C:/Users/Micha/chief add apps/web/middleware.ts
git -C C:/Users/Micha/chief commit -m "feat: protect /onboarding route in middleware"
git -C C:/Users/Micha/chief push
```

---

## Task 4: Onboarding layout (full-screen, no sidebar)

**Files:**
- Create: `apps/web/app/(app)/onboarding/layout.tsx`

- [ ] **Step 1: Create onboarding layout**

```tsx
// apps/web/app/(app)/onboarding/layout.tsx
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';

export default async function OnboardingLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) redirect('/login');

  // If profile already complete, skip onboarding
  const { data: profile } = await supabase
    .from('profiles')
    .select('display_name')
    .eq('id', user.id)
    .maybeSingle();

  if (profile?.display_name) redirect('/today');

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-12">
      {children}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git -C C:/Users/Micha/chief add apps/web/app/\(app\)/onboarding/
git -C C:/Users/Micha/chief commit -m "feat: onboarding layout — full-screen, no sidebar, auth + profile guard"
git -C C:/Users/Micha/chief push
```

---

## Task 5: StepIndicator component

**Files:**
- Create: `apps/web/components/onboarding/StepIndicator.tsx`

- [ ] **Step 1: Create StepIndicator**

```tsx
// apps/web/components/onboarding/StepIndicator.tsx
import { motion } from 'framer-motion';

interface StepIndicatorProps {
  total: number;
  current: number; // 0-indexed
}

export function StepIndicator({ total, current }: StepIndicatorProps) {
  return (
    <div className="flex items-center gap-2">
      {Array.from({ length: total }).map((_, i) => (
        <motion.div
          key={i}
          animate={{
            width: i === current ? 20 : 6,
            backgroundColor: i === current ? '#8A3AFF' : i < current ? 'rgba(138,58,255,0.4)' : 'rgba(247,240,255,0.15)',
          }}
          transition={{ duration: 0.25 }}
          className="h-1.5 rounded-full"
        />
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git -C C:/Users/Micha/chief add apps/web/components/onboarding/
git -C C:/Users/Micha/chief commit -m "feat: StepIndicator component for onboarding wizard"
git -C C:/Users/Micha/chief push
```

---

## Task 6: RoleCard component

**Files:**
- Create: `apps/web/components/onboarding/RoleCard.tsx`

- [ ] **Step 1: Create RoleCard**

```tsx
// apps/web/components/onboarding/RoleCard.tsx
import { cn } from '@/lib/cn';
import type { LucideIcon } from 'lucide-react';

interface RoleCardProps {
  label: string;
  icon: LucideIcon;
  selected: boolean;
  onToggle: () => void;
}

export function RoleCard({ label, icon: Icon, selected, onToggle }: RoleCardProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={cn(
        'relative flex flex-col items-center gap-3 p-4 rounded-[14px] border transition-all duration-150 cursor-pointer select-none text-center',
        selected
          ? 'border-[rgba(138,58,255,0.55)] bg-[rgba(138,58,255,0.10)] shadow-[0_0_0_1px_rgba(138,58,255,0.25)]'
          : 'border-[rgba(247,240,255,0.10)] bg-[rgba(247,240,255,0.03)] hover:border-[rgba(247,240,255,0.18)] hover:bg-[rgba(247,240,255,0.06)]'
      )}
    >
      <div className={cn(
        'w-10 h-10 rounded-[10px] flex items-center justify-center transition-colors',
        selected ? 'bg-[rgba(138,58,255,0.20)]' : 'bg-[rgba(247,240,255,0.06)]'
      )}>
        <Icon size={18} className={selected ? 'text-[var(--v2-violet)]' : 'text-[var(--v2-muted)]'} />
      </div>
      <span className={cn(
        'text-[13px] font-medium transition-colors',
        selected ? 'text-[var(--v2-text)]' : 'text-[var(--v2-muted)]'
      )}>
        {label}
      </span>
      {selected && (
        <div className="absolute top-2.5 right-2.5 w-2 h-2 rounded-full bg-[var(--v2-violet)]" />
      )}
    </button>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git -C C:/Users/Micha/chief add apps/web/components/onboarding/RoleCard.tsx
git -C C:/Users/Micha/chief commit -m "feat: RoleCard selectable card for onboarding role step"
git -C C:/Users/Micha/chief push
```

---

## Task 7: FocusTagInput component

**Files:**
- Create: `apps/web/components/onboarding/FocusTagInput.tsx`

- [ ] **Step 1: Create FocusTagInput**

```tsx
// apps/web/components/onboarding/FocusTagInput.tsx
'use client';
import { useState, useRef } from 'react';
import { X } from 'lucide-react';
import { cn } from '@/lib/cn';

const SUGGESTIONS_BY_ROLE: Record<string, string[]> = {
  Founder: ['Building my startup', 'Fundraising', 'Product launch'],
  Student: ['Master thesis', 'Final exams', 'Research paper'],
  Freelancer: ['Client projects', 'Growing revenue', 'Portfolio site'],
  Engineer: ['Side project', 'Open source', 'Learning Rust'],
  Creator: ['YouTube channel', 'Newsletter', 'Course launch'],
  Other: ['Personal project', 'Learning new skill', 'Health goals'],
};

interface FocusTagInputProps {
  tags: string[];
  onChange: (tags: string[]) => void;
  roles: string[];
  maxTags?: number;
}

export function FocusTagInput({ tags, onChange, roles, maxTags = 3 }: FocusTagInputProps) {
  const [input, setInput] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const suggestions = Array.from(
    new Set(roles.flatMap(r => SUGGESTIONS_BY_ROLE[r] ?? []))
  ).filter(s => !tags.includes(s)).slice(0, 6);

  function addTag(value: string) {
    const trimmed = value.trim();
    if (!trimmed || tags.includes(trimmed) || tags.length >= maxTags) return;
    onChange([...tags, trimmed]);
    setInput('');
  }

  function removeTag(tag: string) {
    onChange(tags.filter(t => t !== tag));
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if ((e.key === 'Enter' || e.key === ',') && input.trim()) {
      e.preventDefault();
      addTag(input);
    }
    if (e.key === 'Backspace' && !input && tags.length > 0) {
      removeTag(tags[tags.length - 1]);
    }
  }

  return (
    <div className="space-y-3">
      <div
        onClick={() => inputRef.current?.focus()}
        className="min-h-[44px] flex flex-wrap gap-2 px-3 py-2.5 rounded-[10px] bg-[rgba(247,240,255,0.04)] border border-[rgba(247,240,255,0.12)] focus-within:border-[var(--v2-border-focus)] transition-colors cursor-text"
      >
        {tags.map(tag => (
          <span
            key={tag}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[rgba(138,58,255,0.15)] border border-[rgba(138,58,255,0.30)] text-[var(--v2-text)] text-[12px] font-medium"
          >
            {tag}
            <button
              type="button"
              onClick={e => { e.stopPropagation(); removeTag(tag); }}
              className="text-[var(--v2-muted)] hover:text-[var(--v2-crit)] transition-colors"
            >
              <X size={11} />
            </button>
          </span>
        ))}
        {tags.length < maxTags && (
          <input
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={() => { if (input.trim()) addTag(input); }}
            placeholder={tags.length === 0 ? 'Type a focus and press Enter…' : ''}
            className="flex-1 min-w-[120px] bg-transparent outline-none text-sm text-[var(--v2-text)] placeholder:text-[var(--v2-subtle)]"
          />
        )}
      </div>
      {suggestions.length > 0 && tags.length < maxTags && (
        <div className="space-y-1.5">
          <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-subtle)]">Suggestions</p>
          <div className="flex flex-wrap gap-2">
            {suggestions.map(s => (
              <button
                key={s}
                type="button"
                onClick={() => addTag(s)}
                className="px-2.5 py-1 rounded-full border border-[rgba(247,240,255,0.12)] bg-[rgba(247,240,255,0.04)] text-[var(--v2-muted)] text-[12px] hover:border-[rgba(138,58,255,0.35)] hover:text-[var(--v2-text)] hover:bg-[rgba(138,58,255,0.08)] transition-all"
              >
                + {s}
              </button>
            ))}
          </div>
        </div>
      )}
      <p className={cn(
        'text-[11px]',
        tags.length >= maxTags ? 'text-[var(--v2-muted)]' : 'text-[var(--v2-subtle)]'
      )}>
        {tags.length}/{maxTags} focuses added
      </p>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git -C C:/Users/Micha/chief add apps/web/components/onboarding/FocusTagInput.tsx
git -C C:/Users/Micha/chief commit -m "feat: FocusTagInput chip input with role-based suggestions"
git -C C:/Users/Micha/chief push
```

---

## Task 8: Onboarding complete API route

**Files:**
- Create: `apps/web/app/api/onboarding/complete/route.ts`

- [ ] **Step 1: Create API route**

```ts
// apps/web/app/api/onboarding/complete/route.ts
import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { z } from 'zod';

const Body = z.object({
  display_name: z.string().min(1).max(100),
  timezone: z.string().min(1),
  roles: z.array(z.string()),
  focuses: z.array(z.string()).max(3),
});

export async function POST(request: Request) {
  const body = await request.json();
  const parsed = Body.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: 'Invalid input' }, { status: 400 });
  }

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const { display_name, timezone, roles, focuses } = parsed.data;

  // Upsert profile
  const { error: profileError } = await supabase
    .from('profiles')
    .upsert({
      id: user.id,
      display_name,
      timezone,
      updated_at: new Date().toISOString(),
    }, { onConflict: 'id' });

  if (profileError) {
    return NextResponse.json({ error: profileError.message }, { status: 500 });
  }

  // Insert goals for each focus
  if (focuses.length > 0) {
    const goals = focuses.map(focus => ({
      user_id: user.id,
      domain: 'projects',
      title: focus,
      status: 'active',
      progress: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }));

    await supabase.from('lg_goals').insert(goals);
  }

  return NextResponse.json({ ok: true });
}
```

- [ ] **Step 2: Commit**

```bash
git -C C:/Users/Micha/chief add apps/web/app/api/onboarding/
git -C C:/Users/Micha/chief commit -m "feat: /api/onboarding/complete writes profile + goals to Supabase"
git -C C:/Users/Micha/chief push
```

---

## Task 9: Onboarding wizard page

**Files:**
- Create: `apps/web/app/(app)/onboarding/page.tsx`

- [ ] **Step 1: Create onboarding/page.tsx**

```tsx
// apps/web/app/(app)/onboarding/page.tsx
'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Rocket, GraduationCap, Briefcase, Code2, Palette, User,
  ArrowRight, Zap,
} from 'lucide-react';
import { Button } from '@/components/design-system';
import { StepIndicator } from '@/components/onboarding/StepIndicator';
import { RoleCard } from '@/components/onboarding/RoleCard';
import { FocusTagInput } from '@/components/onboarding/FocusTagInput';

const ROLES = [
  { label: 'Founder', icon: Rocket },
  { label: 'Student', icon: GraduationCap },
  { label: 'Freelancer', icon: Briefcase },
  { label: 'Engineer', icon: Code2 },
  { label: 'Creator', icon: Palette },
  { label: 'Other', icon: User },
];

const TIMEZONES = [
  'Europe/Berlin', 'Europe/London', 'Europe/Paris', 'America/New_York',
  'America/Los_Angeles', 'America/Chicago', 'Asia/Dubai', 'Asia/Karachi',
  'Asia/Kolkata', 'Asia/Singapore', 'Australia/Sydney', 'Pacific/Auckland',
];

function detectTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch {
    return 'Europe/Berlin';
  }
}

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);

  // Step 1 state
  const [name, setName] = useState('');
  const [timezone, setTimezone] = useState(detectTimezone);

  // Step 2 state
  const [roles, setRoles] = useState<string[]>([]);

  // Step 3 state
  const [focuses, setFocuses] = useState<string[]>([]);

  function toggleRole(label: string) {
    setRoles(prev =>
      prev.includes(label) ? prev.filter(r => r !== label) : [...prev, label]
    );
  }

  async function handleComplete() {
    setSubmitting(true);
    const res = await fetch('/api/onboarding/complete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ display_name: name, timezone, roles, focuses }),
    });
    if (res.ok) {
      router.push('/today');
    } else {
      setSubmitting(false);
    }
  }

  const stepVariants = {
    enter: { opacity: 0, x: 24 },
    center: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: -24 },
  };

  return (
    <div className="w-full max-w-md space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-[linear-gradient(135deg,#2633D9,#8A3AFF)] flex items-center justify-center">
            <Zap size={13} className="text-white" />
          </div>
          <span className="text-sm font-bold tracking-[0.12em] text-[var(--v2-text)] uppercase">Chief</span>
        </div>
        <StepIndicator total={3} current={step} />
      </div>

      <AnimatePresence mode="wait">
        {/* ── Step 0: Name + timezone ── */}
        {step === 0 && (
          <motion.div
            key="step0"
            variants={stepVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.22 }}
            className="space-y-7"
          >
            <div className="space-y-1.5">
              <h1 className="text-2xl font-bold text-[var(--v2-text)]">What should Chief call you?</h1>
              <p className="text-[var(--v2-muted)] text-sm">Used in your Morning Brief and responses.</p>
            </div>
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-[12px] font-medium text-[var(--v2-muted)] uppercase tracking-[0.08em]">
                  Your name
                </label>
                <input
                  type="text"
                  placeholder="Mohamed"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  autoFocus
                  className="w-full h-11 px-3.5 rounded-[10px] bg-[rgba(247,240,255,0.04)] border border-[rgba(247,240,255,0.12)] text-[var(--v2-text)] placeholder:text-[var(--v2-subtle)] text-sm focus:outline-none focus:border-[var(--v2-border-focus)] transition-colors"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-[12px] font-medium text-[var(--v2-muted)] uppercase tracking-[0.08em]">
                  Timezone
                </label>
                <select
                  value={timezone}
                  onChange={e => setTimezone(e.target.value)}
                  className="w-full h-11 px-3.5 rounded-[10px] bg-[rgba(247,240,255,0.04)] border border-[rgba(247,240,255,0.12)] text-[var(--v2-text)] text-sm focus:outline-none focus:border-[var(--v2-border-focus)] transition-colors appearance-none cursor-pointer"
                >
                  {TIMEZONES.map(tz => (
                    <option key={tz} value={tz} className="bg-[#0C1017] text-[var(--v2-text)]">
                      {tz.replace('_', ' ')}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <Button
              variant="solid" size="lg" className="w-full"
              disabled={!name.trim()}
              onClick={() => setStep(1)}
              iconRight={<ArrowRight size={15} />}
            >
              Continue
            </Button>
          </motion.div>
        )}

        {/* ── Step 1: Role ── */}
        {step === 1 && (
          <motion.div
            key="step1"
            variants={stepVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.22 }}
            className="space-y-7"
          >
            <div className="space-y-1.5">
              <h1 className="text-2xl font-bold text-[var(--v2-text)]">What best describes you?</h1>
              <p className="text-[var(--v2-muted)] text-sm">Chief personalizes your brief and suggestions. Pick all that apply.</p>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {ROLES.map(({ label, icon }) => (
                <RoleCard
                  key={label}
                  label={label}
                  icon={icon}
                  selected={roles.includes(label)}
                  onToggle={() => toggleRole(label)}
                />
              ))}
            </div>
            <div className="flex gap-3">
              <Button variant="outline" size="lg" className="flex-1" onClick={() => setStep(0)}>
                Back
              </Button>
              <Button
                variant="solid" size="lg" className="flex-1"
                onClick={() => setStep(2)}
                iconRight={<ArrowRight size={15} />}
              >
                Continue
              </Button>
            </div>
          </motion.div>
        )}

        {/* ── Step 2: Focuses ── */}
        {step === 2 && (
          <motion.div
            key="step2"
            variants={stepVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.22 }}
            className="space-y-7"
          >
            <div className="space-y-1.5">
              <h1 className="text-2xl font-bold text-[var(--v2-text)]">What are you focused on?</h1>
              <p className="text-[var(--v2-muted)] text-sm">
                Chief tracks these as active projects in your Life Graph. Add up to 3.
              </p>
            </div>
            <FocusTagInput
              tags={focuses}
              onChange={setFocuses}
              roles={roles}
              maxTags={3}
            />
            <div className="flex gap-3">
              <Button variant="outline" size="lg" className="flex-1" onClick={() => setStep(1)}>
                Back
              </Button>
              <Button
                variant="solid" size="lg" className="flex-1"
                loading={submitting}
                onClick={handleComplete}
                iconRight={!submitting ? <Zap size={15} /> : undefined}
              >
                Start using Chief
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
```

- [ ] **Step 2: TypeScript check**

```bash
cd C:/Users/Micha/chief/apps/web && npx tsc --noEmit 2>&1 | grep "error TS" | head -10
```

Expected: no errors. Fix any type errors in the new files before continuing.

- [ ] **Step 3: Build check**

```bash
cd C:/Users/Micha/chief/apps/web && npm run build 2>&1 | tail -15
```

Expected: successful build with `/onboarding` appearing as a dynamic route.

- [ ] **Step 4: Commit**

```bash
git -C C:/Users/Micha/chief add apps/web/app/\(app\)/onboarding/ apps/web/components/onboarding/
git -C C:/Users/Micha/chief commit -m "feat: 3-step onboarding wizard (name/timezone → role → focus goals)"
git -C C:/Users/Micha/chief push
```

---

## Verification

1. Run `npm run dev` in `apps/web`
2. Open `http://localhost:3000` → should redirect to `/login`
3. Login page should show split-panel layout (brand panel left, auth card right)
4. Enter email, click Send — should see animated checkmark confirmation
5. Click magic link from email → hits `/callback` → queries `profiles`
6. **First login:** no display_name → redirects to `/onboarding`
7. Onboarding step 1: enter name, confirm timezone, click Continue
8. Step 2: select role cards, click Continue
9. Step 3: add focus tags (suggestions appear based on role), click "Start using Chief"
10. POSTs to `/api/onboarding/complete` → writes `profiles` + `lg_goals` → redirects to `/today`
11. **Second login (same email):** profile exists → redirects to `/today` directly, skips onboarding

---

## Self-Review

**Spec coverage:**
- ✅ Premium split-panel login (Task 1)
- ✅ Animated magic-link sent state with checkmark (Task 1)
- ✅ Callback checks profile, routes new vs returning users (Task 2)
- ✅ Middleware protects /onboarding (Task 3)
- ✅ Full-screen onboarding layout, no sidebar (Task 4)
- ✅ StepIndicator 3-dot animated (Task 5)
- ✅ RoleCard selectable grid (Task 6)
- ✅ FocusTagInput chip input with role suggestions (Task 7)
- ✅ API route writes profiles + lg_goals (Task 8)
- ✅ 3-step wizard page wiring everything together (Task 9)

**Placeholder scan:** No TBDs. All code complete.

**Type consistency:**
- `StepIndicator` props `{total, current}` — used correctly in page.tsx ✅
- `RoleCard` props `{label, icon, selected, onToggle}` — matches usage in page.tsx ✅
- `FocusTagInput` props `{tags, onChange, roles, maxTags}` — matches usage ✅
- `/api/onboarding/complete` body shape `{display_name, timezone, roles, focuses}` — matches `handleComplete()` in page.tsx ✅
- `profiles.display_name` used in callback check — column exists in migration 0001 ✅
- `lg_goals` insert fields match migration schema `{user_id, domain, title, status, progress}` ✅
