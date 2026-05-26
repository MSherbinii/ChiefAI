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
              className="w-full h-10 px-3.5 rounded-[10px] bg-[rgba(247,240,255,0.04)] border border-[rgba(247,240,255,0.12)] text-[var(--v2-text)] placeholder:text-[var(--v2-subtle)] text-sm focus:outline-none focus:border-[var(--v2-border-focus)] transition-colors"
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
