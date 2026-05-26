import { Panel, StatusDot } from '@/components/design-system';
import { Activity, Briefcase, FileText } from 'lucide-react';

type BriefStatus = 'ok' | 'med' | 'high' | 'crit';

interface BriefSection {
  domain: 'body' | 'work' | 'admin';
  label: string;
  agent: string;
  icon: typeof Activity;
  headline: string;
  detail: string;
  status: BriefStatus;
}

interface MorningBriefRealProps {
  sections: BriefSection[];
  greeting: string;
}

export function MorningBriefReal({ sections, greeting }: MorningBriefRealProps) {
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
        {sections.map(s => {
          const Icon = s.icon;
          return (
            <Panel key={s.domain} className="p-4 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Icon size={14} className="text-[var(--v2-violet)]" />
                  <span className="text-[11px] uppercase tracking-[0.08em] font-semibold text-[var(--v2-muted)]">
                    {s.label}
                  </span>
                  <span className="text-[10px] text-[var(--v2-subtle)]">[{s.agent}]</span>
                </div>
                <StatusDot severity={s.status} size="xs" />
              </div>
              <p className="text-sm font-medium text-[var(--v2-text)]">{s.headline}</p>
              <p className="text-[12px] text-[var(--v2-muted)]">{s.detail}</p>
            </Panel>
          );
        })}
      </div>
    </div>
  );
}
