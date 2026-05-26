'use client';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { createClient } from '@/lib/supabase/client';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/design-system';
import { Zap, Mail, Lock, Eye, EyeOff, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/cn';

type Tab = 'signin' | 'signup' | 'reset';

export default function LoginPage() {
  const router = useRouter();
  const supabase = createClient();

  const [tab, setTab] = useState<Tab>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [socialLoading, setSocialLoading] = useState<'google' | 'github' | null>(null);
  const [error, setError] = useState('');
  const [signUpDone, setSignUpDone] = useState(false);
  const [resetSent, setResetSent] = useState(false);

  async function handleSignIn(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });
    if (signInError) {
      setError(signInError.message);
      setLoading(false);
      return;
    }
    const { data: { user } } = await supabase.auth.getUser();
    if (user) {
      const { data: profile } = await supabase
        .from('profiles')
        .select('display_name')
        .eq('id', user.id)
        .maybeSingle();
      router.push(profile?.display_name ? '/today' : '/onboarding');
    }
    setLoading(false);
  }

  async function handleSignUp(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    setLoading(true);
    const { error: signUpError } = await supabase.auth.signUp({
      email,
      password,
      options: { emailRedirectTo: `${location.origin}/callback` },
    });
    if (signUpError) {
      setError(signUpError.message);
      setLoading(false);
      return;
    }
    setSignUpDone(true);
    setLoading(false);
  }

  async function handlePasswordReset(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    const { error: resetError } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${location.origin}/auth/reset-password`,
    });
    if (resetError) {
      setError(resetError.message);
      setLoading(false);
      return;
    }
    setResetSent(true);
    setLoading(false);
  }

  async function handleSocial(provider: 'google' | 'github') {
    setSocialLoading(provider);
    await supabase.auth.signInWithOAuth({
      provider,
      options: { redirectTo: `${location.origin}/callback` },
    });
  }

  const inputCls =
    'w-full h-11 pl-10 pr-4 rounded-[10px] bg-[rgba(247,240,255,0.04)] border border-[rgba(247,240,255,0.12)] text-[var(--v2-text)] placeholder:text-[var(--v2-subtle)] text-sm focus:outline-none focus:border-[var(--v2-border-focus)] transition-colors';

  return (
    <div className="min-h-screen flex flex-col lg:flex-row">
      {/* Left brand panel */}
      <div
        className="hidden lg:flex flex-col justify-between w-1/2 min-h-screen p-12 relative overflow-hidden"
        style={{
          background:
            'radial-gradient(ellipse at 20% 10%, rgba(38,99,235,0.12), transparent 55%), radial-gradient(ellipse at 80% 80%, rgba(138,58,255,0.10), transparent 50%), #08090D',
        }}
      >
        <div className="absolute inset-0 pointer-events-none">
          <div
            className="absolute top-0 left-0 w-96 h-96 rounded-full opacity-[0.04]"
            style={{ background: 'radial-gradient(circle, #8A3AFF, transparent)', transform: 'translate(-30%, -30%)' }}
          />
          <div
            className="absolute bottom-0 right-0 w-80 h-80 rounded-full opacity-[0.03]"
            style={{ background: 'radial-gradient(circle, #18E6D8, transparent)', transform: 'translate(30%, 30%)' }}
          />
        </div>
        <div className="flex items-center gap-2.5 relative z-10">
          <div className="w-8 h-8 rounded-full bg-[linear-gradient(135deg,#2633D9,#8A3AFF)] flex items-center justify-center">
            <Zap size={16} className="text-white" />
          </div>
          <span className="text-sm font-bold tracking-[0.12em] text-[var(--v2-text)] uppercase">Chief</span>
        </div>
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
          <div className="flex items-center gap-3">
            <div className="flex -space-x-2">
              {['#8A3AFF', '#18E6D8', '#F7A93B'].map((color, i) => (
                <div
                  key={i}
                  className="w-7 h-7 rounded-full border-2 border-[#08090D]"
                  style={{ background: color, opacity: 0.7 }}
                />
              ))}
            </div>
            <span className="text-[12px] text-[var(--v2-subtle)]">Used by founders, students &amp; builders</span>
          </div>
        </div>
        <p className="text-[11px] text-[var(--v2-subtle)] relative z-10">© 2026 Chief · Your data stays private</p>
      </div>

      {/* Mobile header */}
      <div className="lg:hidden flex items-center gap-2.5 p-6 border-b border-[var(--v2-border)]">
        <div className="w-7 h-7 rounded-full bg-[linear-gradient(135deg,#2633D9,#8A3AFF)] flex items-center justify-center">
          <Zap size={14} className="text-white" />
        </div>
        <span className="text-sm font-bold tracking-[0.12em] text-[var(--v2-text)] uppercase">Chief</span>
      </div>

      {/* Right auth panel */}
      <div className="flex-1 flex items-center justify-center px-6 py-12 lg:px-16">
        <div className="w-full max-w-sm space-y-6">
          {/* Tab switcher — hidden during reset flow */}
          {tab !== 'reset' && (
            <div className="flex rounded-[10px] p-1 bg-[rgba(247,240,255,0.04)] border border-[rgba(247,240,255,0.08)]">
              {(['signin', 'signup'] as Tab[]).map(t => (
                <button
                  key={t}
                  onClick={() => { setTab(t); setError(''); setSignUpDone(false); }}
                  className={cn(
                    'flex-1 py-2 text-[13px] font-semibold rounded-[8px] transition-all duration-150',
                    tab === t
                      ? 'bg-[linear-gradient(135deg,#2633D9,#8A3AFF)] text-white shadow-[0_0_16px_rgba(89,74,255,0.3)]'
                      : 'text-[var(--v2-muted)] hover:text-[var(--v2-text-dim)]',
                  )}
                >
                  {t === 'signin' ? 'Sign in' : 'Sign up'}
                </button>
              ))}
            </div>
          )}

          {/* Social logins — hidden during reset flow */}
          {tab !== 'reset' && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => handleSocial('google')}
                  disabled={!!socialLoading}
                  className="flex items-center justify-center gap-2 h-11 rounded-[10px] bg-[rgba(247,240,255,0.04)] border border-[rgba(247,240,255,0.12)] text-[var(--v2-text-dim)] text-[13px] font-medium hover:bg-[rgba(247,240,255,0.07)] hover:border-[rgba(247,240,255,0.18)] transition-all disabled:opacity-50"
                >
                  {socialLoading === 'google' ? (
                    <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
                      <path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4" viewBox="0 0 24 24">
                      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                    </svg>
                  )}
                  Google
                </button>
                <button
                  onClick={() => handleSocial('github')}
                  disabled={!!socialLoading}
                  className="flex items-center justify-center gap-2 h-11 rounded-[10px] bg-[rgba(247,240,255,0.04)] border border-[rgba(247,240,255,0.12)] text-[var(--v2-text-dim)] text-[13px] font-medium hover:bg-[rgba(247,240,255,0.07)] hover:border-[rgba(247,240,255,0.18)] transition-all disabled:opacity-50"
                >
                  {socialLoading === 'github' ? (
                    <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
                      <path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
                      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
                    </svg>
                  )}
                  GitHub
                </button>
              </div>

              {/* Divider */}
              <div className="flex items-center gap-3">
                <div className="flex-1 h-px bg-[rgba(247,240,255,0.08)]" />
                <span className="text-[11px] text-[var(--v2-subtle)] uppercase tracking-[0.08em]">or</span>
                <div className="flex-1 h-px bg-[rgba(247,240,255,0.08)]" />
              </div>
            </>
          )}

          {/* Forms */}
          <AnimatePresence mode="wait">
            {signUpDone ? (
              <motion.div
                key="done"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-4 text-center py-4"
              >
                <motion.div
                  initial={{ scale: 0.5, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ type: 'spring', stiffness: 200, damping: 18 }}
                  className="w-14 h-14 rounded-full bg-[rgba(56,242,168,0.10)] border border-[rgba(56,242,168,0.20)] flex items-center justify-center mx-auto"
                >
                  <CheckCircle size={26} className="text-[var(--v2-ok)]" />
                </motion.div>
                <div className="space-y-1.5">
                  <h3 className="text-lg font-bold text-[var(--v2-text)]">Check your email</h3>
                  <p className="text-[var(--v2-muted)] text-sm">
                    We sent a confirmation link to<br />
                    <strong className="text-[var(--v2-text)]">{email}</strong>
                  </p>
                </div>
                <button
                  onClick={() => { setSignUpDone(false); setTab('signin'); }}
                  className="text-[12px] text-[var(--v2-violet)] hover:underline"
                >
                  Back to sign in
                </button>
              </motion.div>
            ) : tab === 'signin' ? (
              <motion.form
                key="signin"
                initial={{ opacity: 0, x: -16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 16 }}
                transition={{ duration: 0.18 }}
                onSubmit={handleSignIn}
                className="space-y-4"
              >
                <div className="space-y-1.5">
                  <label className="text-[12px] font-medium text-[var(--v2-muted)] uppercase tracking-[0.08em]">
                    Email
                  </label>
                  <div className="relative">
                    <Mail size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--v2-subtle)]" />
                    <input
                      type="email"
                      value={email}
                      onChange={e => setEmail(e.target.value)}
                      required
                      placeholder="you@example.com"
                      className={inputCls}
                    />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label className="text-[12px] font-medium text-[var(--v2-muted)] uppercase tracking-[0.08em]">
                      Password
                    </label>
                    <button
                      type="button"
                      onClick={() => { setTab('reset'); setError(''); }}
                      className="text-[11px] text-[var(--v2-violet)] hover:underline"
                    >
                      Forgot password?
                    </button>
                  </div>
                  <div className="relative">
                    <Lock size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--v2-subtle)]" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      required
                      placeholder="••••••••"
                      className={cn(inputCls, 'pr-11')}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(v => !v)}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[var(--v2-subtle)] hover:text-[var(--v2-muted)]"
                    >
                      {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                    </button>
                  </div>
                </div>
                {error && <p className="text-[12px] text-[var(--v2-crit)]">{error}</p>}
                <Button variant="solid" size="lg" className="w-full" loading={loading} type="submit">
                  Sign in
                </Button>
              </motion.form>
            ) : tab === 'signup' ? (
              <motion.form
                key="signup"
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16 }}
                transition={{ duration: 0.18 }}
                onSubmit={handleSignUp}
                className="space-y-4"
              >
                <div className="space-y-1.5">
                  <label className="text-[12px] font-medium text-[var(--v2-muted)] uppercase tracking-[0.08em]">
                    Email
                  </label>
                  <div className="relative">
                    <Mail size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--v2-subtle)]" />
                    <input
                      type="email"
                      value={email}
                      onChange={e => setEmail(e.target.value)}
                      required
                      placeholder="you@example.com"
                      className={inputCls}
                    />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <label className="text-[12px] font-medium text-[var(--v2-muted)] uppercase tracking-[0.08em]">
                    Password
                  </label>
                  <div className="relative">
                    <Lock size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--v2-subtle)]" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      required
                      placeholder="Min. 8 characters"
                      className={cn(inputCls, 'pr-11')}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(v => !v)}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[var(--v2-subtle)] hover:text-[var(--v2-muted)]"
                    >
                      {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                    </button>
                  </div>
                </div>
                <div className="space-y-1.5">
                  <label className="text-[12px] font-medium text-[var(--v2-muted)] uppercase tracking-[0.08em]">
                    Confirm password
                  </label>
                  <div className="relative">
                    <Lock size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--v2-subtle)]" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={confirmPassword}
                      onChange={e => setConfirmPassword(e.target.value)}
                      required
                      placeholder="••••••••"
                      className={inputCls}
                    />
                  </div>
                </div>
                {error && <p className="text-[12px] text-[var(--v2-crit)]">{error}</p>}
                <Button variant="solid" size="lg" className="w-full" loading={loading} type="submit">
                  Create account
                </Button>
                <p className="text-[11px] text-[var(--v2-subtle)] text-center">
                  By signing up you agree to our terms. No spam.
                </p>
              </motion.form>
            ) : tab === 'reset' && !resetSent ? (
              <motion.form
                key="reset"
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16 }}
                transition={{ duration: 0.18 }}
                onSubmit={handlePasswordReset}
                className="space-y-4"
              >
                <div className="space-y-1.5">
                  <h3 className="text-lg font-bold text-[var(--v2-text)]">Reset password</h3>
                  <p className="text-[var(--v2-muted)] text-sm">Enter your email and we'll send a reset link.</p>
                </div>
                <div className="space-y-1.5">
                  <label className="text-[12px] font-medium text-[var(--v2-muted)] uppercase tracking-[0.08em]">Email</label>
                  <div className="relative">
                    <Mail size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--v2-subtle)]" />
                    <input
                      type="email"
                      value={email}
                      onChange={e => setEmail(e.target.value)}
                      required
                      placeholder="you@example.com"
                      className={inputCls}
                    />
                  </div>
                </div>
                {error && <p className="text-[12px] text-[var(--v2-crit)]">{error}</p>}
                <div className="flex gap-3">
                  <Button variant="outline" size="lg" className="flex-1" type="button" onClick={() => { setTab('signin'); setError(''); }}>
                    Back
                  </Button>
                  <Button variant="solid" size="lg" className="flex-1" loading={loading} type="submit">
                    Send reset link
                  </Button>
                </div>
              </motion.form>
            ) : (
              <motion.div
                key="reset-sent"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-4 text-center py-2"
              >
                <motion.div
                  initial={{ scale: 0.5, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ type: 'spring', stiffness: 200, damping: 18 }}
                  className="w-14 h-14 rounded-full bg-[rgba(56,242,168,0.10)] border border-[rgba(56,242,168,0.20)] flex items-center justify-center mx-auto"
                >
                  <CheckCircle size={26} className="text-[var(--v2-ok)]" />
                </motion.div>
                <div className="space-y-1.5">
                  <h3 className="text-lg font-bold text-[var(--v2-text)]">Check your email</h3>
                  <p className="text-[var(--v2-muted)] text-sm">
                    Reset link sent to<br /><strong className="text-[var(--v2-text)]">{email}</strong>
                  </p>
                </div>
                <button
                  onClick={() => { setTab('signin'); setResetSent(false); }}
                  className="text-[12px] text-[var(--v2-violet)] hover:underline"
                >
                  Back to sign in
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
