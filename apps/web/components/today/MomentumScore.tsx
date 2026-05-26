'use client';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface DomainScore {
  label: string;
  value: number;
  color: string;
}

interface MomentumScoreProps {
  total: number;
  domains: DomainScore[];
  previousTotal?: number;
  history?: { total: number; scored_at: string }[];
}

export function MomentumScore({ total, domains, previousTotal, history }: MomentumScoreProps) {
  const circumference = 2 * Math.PI * 36;
  const progress = (total / 100) * circumference;

  const delta = previousTotal != null ? total - previousTotal : null;
  const DeltaIcon = delta == null ? null : delta > 0 ? TrendingUp : delta < 0 ? TrendingDown : Minus;
  const deltaColor = delta == null ? '' : delta > 0 ? 'text-[var(--v2-ok)]' : delta < 0 ? 'text-[var(--v2-crit)]' : 'text-[var(--v2-muted)]';

  // Sparkline from history (last 7 days)
  const sparkValues = history?.map(h => h.total) ?? [];
  const sparkMax = Math.max(...sparkValues, 100);
  const sparkMin = Math.min(...sparkValues, 0);
  const sparkRange = sparkMax - sparkMin || 1;

  return (
    <div className="flex flex-col gap-4 p-5 rounded-[16px] border border-[rgba(247,240,255,0.10)] [background:linear-gradient(180deg,rgba(18,24,34,0.98),rgba(11,15,22,0.98))] shadow-[inset_0_1px_0_rgba(255,255,255,0.035),0_18px_55px_rgba(0,0,0,0.38)]">
      <div className="flex items-center gap-6">
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

        {/* Domain bars + delta */}
        <div className="flex-1 space-y-2">
          {/* Delta badge */}
          {delta !== null && DeltaIcon && (
            <div className={`flex items-center gap-1.5 text-[11px] font-semibold ${deltaColor}`}>
              <DeltaIcon size={11} />
              {delta > 0 ? `+${delta}` : delta === 0 ? 'Stable' : delta} vs yesterday
            </div>
          )}
          {/* Domain bars */}
          <div className="grid grid-cols-2 gap-x-6 gap-y-2">
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
      </div>

      {/* 7-day sparkline */}
      {sparkValues.length > 1 && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase tracking-[0.08em] text-[var(--v2-subtle)]">7-day trend</span>
            <span className="text-[10px] text-[var(--v2-subtle)]">{sparkValues[0]} → {sparkValues[sparkValues.length - 1]}</span>
          </div>
          <div className="flex items-end gap-1 h-8">
            {sparkValues.map((v, i) => {
              const h = Math.max(2, ((v - sparkMin) / sparkRange) * 32);
              const isLatest = i === sparkValues.length - 1;
              return (
                <motion.div
                  key={i}
                  initial={{ height: 0 }}
                  animate={{ height: h }}
                  transition={{ delay: i * 0.05, duration: 0.4 }}
                  className="flex-1 rounded-sm"
                  style={{
                    background: isLatest ? '#8A3AFF' : 'rgba(138,58,255,0.3)',
                  }}
                  title={`${v}`}
                />
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
