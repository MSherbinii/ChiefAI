'use client';
import { motion } from 'framer-motion';

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
