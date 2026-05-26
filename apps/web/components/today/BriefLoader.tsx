'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Zap } from 'lucide-react';
import { motion } from 'framer-motion';

interface BriefLoaderProps {
  userId: string;
  userName: string;
}

export function BriefLoader({ userId: _userId, userName: _userName }: BriefLoaderProps) {
  const router = useRouter();
  const [status, setStatus] = useState<'generating' | 'done' | 'error'>('generating');
  const [step, setStep] = useState(0);

  const steps = [
    'Analyzing your health data…',
    'Checking stale communications…',
    'Reviewing project velocity…',
    'Calculating momentum score…',
    'Generating your brief…',
  ];

  useEffect(() => {
    let stepTimer: ReturnType<typeof setInterval>;

    async function generate() {
      stepTimer = setInterval(() => setStep(s => Math.min(s + 1, steps.length - 1)), 1500);

      try {
        // Trigger score first (fast)
        await fetch('/api/agent/score', { method: 'POST' });

        // Then brief (slower)
        const res = await fetch('/api/agent/brief', { method: 'POST' });

        if (res.ok) {
          setStatus('done');
          clearInterval(stepTimer);
          setTimeout(() => router.refresh(), 500);
        } else {
          setStatus('error');
          clearInterval(stepTimer);
        }
      } catch {
        setStatus('error');
        clearInterval(stepTimer);
      }
    }

    generate();
    return () => clearInterval(stepTimer);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (status === 'error') {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center space-y-3">
        <p className="text-[13px] text-[var(--v2-muted)]">
          Brief generation failed. Make sure the agent service is running.
        </p>
        <button
          onClick={() => router.refresh()}
          className="text-[12px] text-[var(--v2-violet)] hover:underline"
        >
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center h-64 text-center space-y-5">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
        className="w-10 h-10 rounded-full bg-[linear-gradient(135deg,#2633D9,#8A3AFF)] flex items-center justify-center"
      >
        <Zap size={18} className="text-white" />
      </motion.div>
      <div className="space-y-1.5">
        <p className="text-sm font-medium text-[var(--v2-text)]">Building your Morning Brief</p>
        <motion.p
          key={step}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-[12px] text-[var(--v2-muted)]"
        >
          {steps[step]}
        </motion.p>
      </div>
    </div>
  );
}
