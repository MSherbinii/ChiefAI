import { Panel, StatusDot } from '@/components/design-system';

export function HealthDomain({ data }: { data: any }) {
  const { recoveries, sleeps, workouts } = data;

  const latestRecovery = recoveries[0]?.value?.recovery_score;
  const avgSleep = sleeps.length > 0
    ? sleeps.reduce((s: number, r: any) => s + (r.value?.duration_minutes ?? 0), 0) / sleeps.length
    : null;

  const recoveryStatus = latestRecovery >= 67 ? 'ok' : latestRecovery >= 34 ? 'med' : latestRecovery != null ? 'high' : 'info';

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <Panel className="p-4 text-center space-y-1">
          <div className="flex justify-center mb-1"><StatusDot severity={recoveryStatus as any} size="md" /></div>
          <p className="text-2xl font-bold text-[var(--v2-text)]">{latestRecovery != null ? `${latestRecovery.toFixed(0)}%` : '—'}</p>
          <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-muted)]">Recovery</p>
        </Panel>
        <Panel className="p-4 text-center space-y-1">
          <p className="text-2xl font-bold text-[var(--v2-text)]">{avgSleep != null ? `${(avgSleep / 60).toFixed(1)}h` : '—'}</p>
          <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-muted)]">Avg Sleep</p>
        </Panel>
        <Panel className="p-4 text-center space-y-1">
          <p className="text-2xl font-bold text-[var(--v2-text)]">{workouts.length}</p>
          <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-muted)]">Workouts</p>
        </Panel>
      </div>
      {recoveries.length === 0 && (
        <p className="text-[13px] text-[var(--v2-muted)]">Connect WHOOP to see health data.</p>
      )}
      {recoveries.length > 0 && (
        <div className="space-y-2">
          <p className="text-[12px] uppercase tracking-[0.08em] text-[var(--v2-muted)]">Recovery (7d)</p>
          <div className="flex items-end gap-1.5 h-16">
            {recoveries.slice().reverse().map((r: any, i: number) => {
              const score = r.value?.recovery_score ?? 0;
              const h = Math.max(4, (score / 100) * 64);
              const color = score >= 67 ? '#38F2A8' : score >= 34 ? '#F7A93B' : '#FF4F6D';
              return <div key={i} className="flex-1 rounded-sm" style={{ height: h, backgroundColor: color, opacity: 0.7 }} />;
            })}
          </div>
        </div>
      )}
    </div>
  );
}
