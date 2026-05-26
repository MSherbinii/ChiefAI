// apps/web/components/today/MorningBriefReal.tsx
import { Panel, StatusDot } from '@/components/design-system';
import { Activity, Briefcase, FileText, DollarSign, ArrowRight } from 'lucide-react';

type BriefStatus = 'ok' | 'med' | 'high' | 'crit';

export interface AiBriefSection {
  domain: string;
  agent: string;
  status: BriefStatus;
  headline: string;
  detail: string;
  action?: string;
}

interface MorningBriefRealProps {
  greeting: string;
  sections: AiBriefSection[];
  bestMove?: string;
  patterns?: string[];
}

const DOMAIN_ICONS: Record<string, React.ElementType> = {
  body:  Activity,
  work:  Briefcase,
  admin: FileText,
  money: DollarSign,
};

export function MorningBriefReal({ greeting, sections, bestMove, patterns }: MorningBriefRealProps) {
  if (sections.length === 0) {
    return (
      <div className="text-[13px] text-[var(--v2-muted)]">
        Syncing your data… check back in a moment.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-[var(--v2-text)]">{greeting}</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {sections.map((s, i) => {
          const Icon = DOMAIN_ICONS[s.domain] ?? Activity;
          return (
            <Panel key={i} className="p-4 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Icon size={14} className="text-[var(--v2-violet)]" />
                  <span className="text-[11px] uppercase tracking-[0.08em] font-semibold text-[var(--v2-muted)]">
                    {s.domain}
                  </span>
                  <span className="text-[10px] text-[var(--v2-subtle)]">[{s.agent}]</span>
                </div>
                <StatusDot severity={s.status as any} size="xs" />
              </div>
              <p className="text-sm font-medium text-[var(--v2-text)]">{s.headline}</p>
              <p className="text-[12px] text-[var(--v2-muted)]">{s.detail}</p>
              {s.action && (
                <p className="text-[12px] text-[var(--v2-violet)] flex items-center gap-1">
                  <ArrowRight size={11} />
                  {s.action}
                </p>
              )}
            </Panel>
          );
        })}
      </div>

      {bestMove && (
        <Panel variant="elevated" className="p-4">
          <div className="flex items-start gap-3">
            <div className="w-1.5 h-full min-h-[20px] rounded-full bg-[var(--v2-violet)] flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-muted)] mb-1">Today&apos;s best move</p>
              <p className="text-sm text-[var(--v2-text)]">{bestMove}</p>
            </div>
          </div>
        </Panel>
      )}

      {patterns && patterns.length > 0 && (
        <div className="space-y-1">
          <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-subtle)]">Patterns Chief noticed</p>
          {patterns.map((p, i) => (
            <p key={i} className="text-[12px] text-[var(--v2-muted)] italic">{p}</p>
          ))}
        </div>
      )}
    </div>
  );
}
