import { Panel, StatusDot } from '@/components/design-system';

export function AdminDomain({ data }: { data: any }) {
  const { documents, pendingQueue } = data;
  const now = new Date();
  const expiringSoon = documents.filter((d: any) => {
    if (!d.expires_at) return false;
    const exp = new Date(d.expires_at);
    return (exp.getTime() - now.getTime()) < 30 * 24 * 60 * 60 * 1000;
  });

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <Panel className="p-4 text-center space-y-1">
          <p className="text-2xl font-bold text-[var(--v2-text)]">{documents.length}</p>
          <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-muted)]">Documents</p>
        </Panel>
        <Panel className="p-4 text-center space-y-1">
          <p className="text-2xl font-bold text-[var(--v2-text)]">{expiringSoon.length}</p>
          <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-muted)]">Expiring Soon</p>
        </Panel>
        <Panel className="p-4 text-center space-y-1">
          <p className="text-2xl font-bold text-[var(--v2-text)]">{pendingQueue.length}</p>
          <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-muted)]">In Queue</p>
        </Panel>
      </div>
      {documents.length === 0 && (
        <p className="text-[13px] text-[var(--v2-muted)]">Upload documents (insurance card, ID, contracts) to build your document library.</p>
      )}
      {pendingQueue.length > 0 && (
        <div className="space-y-2">
          <p className="text-[12px] uppercase tracking-[0.08em] text-[var(--v2-muted)]">Approval Queue</p>
          {pendingQueue.map((q: any, i: number) => (
            <Panel key={i} className="p-3 flex items-center gap-3">
              <StatusDot severity={q.risk_level === 'confirm' ? 'high' : 'med'} size="xs" />
              <div className="flex-1 min-w-0">
                <p className="text-[13px] text-[var(--v2-text)] truncate">{q.title}</p>
                <p className="text-[11px] text-[var(--v2-muted)]">[{q.agent}]</p>
              </div>
            </Panel>
          ))}
        </div>
      )}
    </div>
  );
}
