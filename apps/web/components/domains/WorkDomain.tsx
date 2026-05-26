import { Panel } from '@/components/design-system';

export function WorkDomain({ data }: { data: any }) {
  const { commits, projects, staleComms } = data;
  const repoSet = new Set(commits.map((c: any) => c.value?.repo).filter(Boolean));

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <Panel className="p-4 text-center space-y-1">
          <p className="text-2xl font-bold text-[var(--v2-text)]">{commits.length}</p>
          <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-muted)]">Commits</p>
        </Panel>
        <Panel className="p-4 text-center space-y-1">
          <p className="text-2xl font-bold text-[var(--v2-text)]">{repoSet.size}</p>
          <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-muted)]">Repos Active</p>
        </Panel>
        <Panel className="p-4 text-center space-y-1">
          <p className="text-2xl font-bold text-[var(--v2-text)]">{staleComms.length}</p>
          <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-muted)]">Stale Threads</p>
        </Panel>
      </div>
      {projects.length > 0 && (
        <div className="space-y-2">
          <p className="text-[12px] uppercase tracking-[0.08em] text-[var(--v2-muted)]">Active Projects</p>
          {projects.map((p: any) => (
            <Panel key={p.name} className="p-3 flex items-center justify-between">
              <span className="text-[13px] text-[var(--v2-text)]">{p.name}</span>
              {p.deadline && <span className="text-[11px] text-[var(--v2-muted)]">Due {p.deadline}</span>}
            </Panel>
          ))}
        </div>
      )}
      {staleComms.length > 0 && (
        <div className="space-y-2">
          <p className="text-[12px] uppercase tracking-[0.08em] text-[var(--v2-muted)]">Needs Reply</p>
          {staleComms.slice(0, 5).map((t: any, i: number) => (
            <Panel key={i} className="p-3">
              <p className="text-[13px] text-[var(--v2-text)] truncate">{t.subject || '(no subject)'}</p>
              <p className="text-[11px] text-[var(--v2-muted)]">{t.staleness_days ?? '?'}d old · {t.channel}</p>
            </Panel>
          ))}
        </div>
      )}
    </div>
  );
}
