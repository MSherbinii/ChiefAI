// apps/web/components/replay/WeeklyReplay.tsx
import { Panel } from '@/components/design-system';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface CheckIn {
  id: string;
  type: string;
  narrative: string | null;
  highlights: string[] | null;
  lowlights: string[] | null;
  patterns_noticed: string[] | null;
  momentum_start: number | null;
  momentum_end: number | null;
  actions_planned: string[] | null;
  actions_completed: string[] | null;
  created_at: string;
}

interface WeeklyReplayProps {
  checkIns: CheckIn[];
  currentScore: number | null;
}

export function WeeklyReplay({ checkIns, currentScore }: WeeklyReplayProps) {
  if (checkIns.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center space-y-3">
        <p className="text-sm font-medium text-[var(--v2-text)]">No replays yet.</p>
        <p className="text-[13px] text-[var(--v2-muted)] max-w-xs">
          Your Weekly Replay appears here after Chief generates your first Morning Brief.
          Connect Gmail to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {checkIns.map(ci => {
        const delta = (ci.momentum_end ?? 0) - (ci.momentum_start ?? 0);
        const TrendIcon = delta > 0 ? TrendingUp : delta < 0 ? TrendingDown : Minus;
        const trendColor = delta > 0 ? 'text-[var(--v2-ok)]' : delta < 0 ? 'text-[var(--v2-crit)]' : 'text-[var(--v2-muted)]';
        const date = new Date(ci.created_at).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });

        return (
          <Panel key={ci.id} className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[12px] uppercase tracking-[0.08em] text-[var(--v2-muted)]">{date}</span>
              {(ci.momentum_start || ci.momentum_end) && (
                <div className={`flex items-center gap-1.5 text-[12px] font-semibold ${trendColor}`}>
                  <TrendIcon size={13} />
                  {ci.momentum_start} → {ci.momentum_end}
                  {delta !== 0 && <span>({delta > 0 ? '+' : ''}{delta})</span>}
                </div>
              )}
            </div>

            {ci.narrative && (
              <p className="text-sm text-[var(--v2-text-dim)] leading-relaxed">{ci.narrative}</p>
            )}

            {ci.highlights && ci.highlights.length > 0 && (
              <div className="space-y-1">
                <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-ok)]">Highlights</p>
                {ci.highlights.map((h, i) => (
                  <p key={i} className="text-[12px] text-[var(--v2-muted)]">• {h}</p>
                ))}
              </div>
            )}

            {ci.lowlights && ci.lowlights.length > 0 && (
              <div className="space-y-1">
                <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-crit)]">Lowlights</p>
                {ci.lowlights.map((l, i) => (
                  <p key={i} className="text-[12px] text-[var(--v2-muted)]">• {l}</p>
                ))}
              </div>
            )}

            {ci.patterns_noticed && ci.patterns_noticed.length > 0 && (
              <div className="space-y-1">
                <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-violet)]">Patterns noticed</p>
                {ci.patterns_noticed.map((p, i) => (
                  <p key={i} className="text-[12px] text-[var(--v2-muted)] italic">{p}</p>
                ))}
              </div>
            )}
          </Panel>
        );
      })}
    </div>
  );
}
