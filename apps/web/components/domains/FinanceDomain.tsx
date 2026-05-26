import { Panel } from '@/components/design-system';

export function FinanceDomain({ data }: { data: any }) {
  const { transactions, subscriptions } = data;
  const totalSpent = transactions.reduce((s: number, t: any) => s + Math.abs(t.amount_cents ?? 0), 0) / 100;
  const totalSubs = subscriptions.reduce((s: number, t: any) => s + Math.abs(t.amount_cents ?? 0), 0) / 100;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <Panel className="p-4 text-center space-y-1">
          <p className="text-2xl font-bold text-[var(--v2-text)]">€{totalSpent.toFixed(0)}</p>
          <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-muted)]">Spent (30d)</p>
        </Panel>
        <Panel className="p-4 text-center space-y-1">
          <p className="text-2xl font-bold text-[var(--v2-text)]">€{totalSubs.toFixed(0)}</p>
          <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-muted)]">Subscriptions/mo</p>
        </Panel>
      </div>
      {transactions.length === 0 && (
        <p className="text-[13px] text-[var(--v2-muted)]">Connect a bank account to see spending data.</p>
      )}
      {subscriptions.length > 0 && (
        <div className="space-y-2">
          <p className="text-[12px] uppercase tracking-[0.08em] text-[var(--v2-muted)]">Subscriptions</p>
          {subscriptions.map((s: any, i: number) => (
            <Panel key={i} className="p-3 flex items-center justify-between">
              <span className="text-[13px] text-[var(--v2-text)]">{s.description || 'Unknown'}</span>
              <span className="text-[12px] text-[var(--v2-muted)]">€{(Math.abs(s.amount_cents ?? 0) / 100).toFixed(2)}/{s.recurring_period ?? 'mo'}</span>
            </Panel>
          ))}
        </div>
      )}
    </div>
  );
}
