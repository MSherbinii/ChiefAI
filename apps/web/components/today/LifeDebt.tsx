// apps/web/components/today/LifeDebt.tsx
import { Panel } from '@/components/design-system';
import { AlertCircle } from 'lucide-react';

interface DebtItem {
  domain: string;
  count: number;
  description: string;
}

interface LifeDebtProps {
  total: number;
  items: DebtItem[];
}

const DOMAIN_COLORS: Record<string, string> = {
  communication: 'text-[var(--v2-violet)]',
  financial:     'text-[var(--v2-warn)]',
  health:        'text-[var(--v2-teal)]',
  admin:         'text-[var(--v2-info)]',
  work:          'text-[var(--v2-ok)]',
};

export function LifeDebt({ total, items }: LifeDebtProps) {
  if (total === 0) return null;

  return (
    <Panel variant="inset" className="p-4 space-y-3">
      <div className="flex items-center gap-2">
        <AlertCircle size={14} className="text-[var(--v2-warn)]" />
        <span className="text-[12px] font-semibold uppercase tracking-[0.08em] text-[var(--v2-warn)]">
          Life Debt — {total} item{total !== 1 ? 's' : ''}
        </span>
      </div>
      <div className="space-y-1.5">
        {items.map((item, i) => (
          <div key={i} className="flex items-start gap-2">
            <span className={`text-[11px] font-semibold uppercase tracking-wider mt-0.5 ${DOMAIN_COLORS[item.domain] ?? 'text-[var(--v2-muted)]'}`}>
              {item.domain}
            </span>
            <span className="text-[12px] text-[var(--v2-text-dim)]">{item.description}</span>
          </div>
        ))}
      </div>
      <p className="text-[11px] text-[var(--v2-subtle)] italic">
        Want to clear 3 today? Ask Chief to pick the highest-impact ones.
      </p>
    </Panel>
  );
}
