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
      {/* Left: brand panel */}
      <div className="hidden lg:flex flex-col justify-between w-1/2 min-h-screen p-12 relative overflow-hidden"
        style={{ background: 'radial-gradient(ellipse at 20% 10%, rgba(38,99,235,0.12), transparent 55%), radial-gradient(ellipse at 80% 80%, rgba(138,58,255,0.10), transparent 50%), #08090D' }}>
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-0 left-0 w-96 h-96 rounded-full opacity-[0.04]"
            style={{ background: 'radial-gradient(circle, #8A3AFF, transparent)', transform: 'translate(-30%, -30%)' }} />
          <div className="absolute bottom-0 right-0 w-80 h-80 rounded-full opacity-[0.03]"
            style={{ background: 'radial-gradient(circle, #18E6D8, transparent)', transform: 'translate(30%, 30%)' }} />
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
                <div key={i} className="w-7 h-7 rounded-full border-2 border-[#08090D]"
                  style={{ background: color, opacity: 0.7 }} />
              ))}
            </div>
            <span className="text-[12px] text-[var(--v2-subtle)]">Used by founders, students &amp; builders</span>
          </div>
        </div>
        <p className="text-[11px] text-[var(--v2-subtle)] relative z-10">
          © 2026 Chief · Your data stays private
        </p>
      </div>

      {/* Mobile header */}
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
                    Enter your email and we&apos;ll send a magic link.
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
