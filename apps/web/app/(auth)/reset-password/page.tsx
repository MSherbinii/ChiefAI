'use client';
import { useState, useEffect } from 'react';
import { createClient } from '@/lib/supabase/client';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/design-system';
import { Lock, Eye, EyeOff, CheckCircle, Zap } from 'lucide-react';
import { motion } from 'framer-motion';

export default function ResetPasswordPage() {
  const router = useRouter();
  const supabase = createClient();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // Supabase puts the session in the URL hash after clicking reset link
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event) => {
      if (event === 'PASSWORD_RECOVERY') {
        setReady(true);
      }
    });
    return () => subscription.unsubscribe();
  }, [supabase.auth]);

  async function handleReset(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (password !== confirmPassword) { setError('Passwords do not match'); return; }
    if (password.length < 8) { setError('Password must be at least 8 characters'); return; }
    setLoading(true);
    const { error: updateError } = await supabase.auth.updateUser({ password });
    if (updateError) {
      setError(updateError.message);
      setLoading(false);
      return;
    }
    setDone(true);
    setTimeout(() => router.push('/today'), 2000);
  }

  const inputCls = 'w-full h-11 pl-10 pr-12 rounded-[10px] bg-[rgba(247,240,255,0.04)] border border-[rgba(247,240,255,0.12)] text-[var(--v2-text)] placeholder:text-[var(--v2-subtle)] text-sm focus:outline-none focus:border-[var(--v2-border-focus)] transition-colors';

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm space-y-7">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-full bg-[linear-gradient(135deg,#2633D9,#8A3AFF)] flex items-center justify-center">
            <Zap size={13} className="text-white" />
          </div>
          <span className="text-sm font-bold tracking-[0.12em] text-[var(--v2-text)] uppercase">Chief</span>
        </div>

        {done ? (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-4 text-center py-4">
            <motion.div
              initial={{ scale: 0.5, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: 'spring', stiffness: 200, damping: 18 }}
              className="w-14 h-14 rounded-full bg-[rgba(56,242,168,0.10)] border border-[rgba(56,242,168,0.20)] flex items-center justify-center mx-auto"
            >
              <CheckCircle size={26} className="text-[var(--v2-ok)]" />
            </motion.div>
            <div className="space-y-1.5">
              <h2 className="text-xl font-bold text-[var(--v2-text)]">Password updated</h2>
              <p className="text-[var(--v2-muted)] text-sm">Redirecting you to Chief…</p>
            </div>
          </motion.div>
        ) : !ready ? (
          <div className="space-y-3">
            <h2 className="text-2xl font-bold text-[var(--v2-text)]">Set new password</h2>
            <p className="text-[var(--v2-muted)] text-sm">Waiting for authentication… If this takes too long, request a new reset link.</p>
            <Button variant="outline" size="md" onClick={() => router.push('/login')}>Back to sign in</Button>
          </div>
        ) : (
          <form onSubmit={handleReset} className="space-y-5">
            <div className="space-y-1.5">
              <h2 className="text-2xl font-bold text-[var(--v2-text)]">Set new password</h2>
              <p className="text-[var(--v2-muted)] text-sm">Choose a strong password for your account.</p>
            </div>
            <div className="space-y-1.5">
              <label className="text-[12px] font-medium text-[var(--v2-muted)] uppercase tracking-[0.08em]">New password</label>
              <div className="relative">
                <Lock size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--v2-subtle)]" />
                <input type={showPassword ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)} required placeholder="Min. 8 characters" className={inputCls} />
                <button type="button" onClick={() => setShowPassword(v => !v)} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[var(--v2-subtle)] hover:text-[var(--v2-muted)]">
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-[12px] font-medium text-[var(--v2-muted)] uppercase tracking-[0.08em]">Confirm password</label>
              <div className="relative">
                <Lock size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--v2-subtle)]" />
                <input type={showPassword ? 'text' : 'password'} value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} required placeholder="••••••••" className={inputCls} />
              </div>
            </div>
            {error && <p className="text-[12px] text-[var(--v2-crit)]">{error}</p>}
            <Button variant="solid" size="lg" className="w-full" loading={loading} type="submit">
              Update password
            </Button>
          </form>
        )}
      </div>
    </div>
  );
}
