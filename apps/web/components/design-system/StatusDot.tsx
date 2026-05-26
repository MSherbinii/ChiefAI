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
