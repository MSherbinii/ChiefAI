import { Panel, StatusDot } from '@/components/design-system';
import { Activity, Mail, GitBranch, DollarSign, FileText, Search, Zap } from 'lucide-react';

const AGENTS = [
  { name: 'Chief',  icon: Zap,        desc: 'Orchestrator — synthesizes all domains' },
  { name: 'Pulse',  icon: Activity,   desc: 'Health — recovery, sleep, training, nutrition' },
  { name: 'Echo',   icon: Mail,       desc: 'Communication — emails, threads, follow-ups' },
  { name: 'Forge',  icon: GitBranch,  desc: 'Projects — GitHub, thesis, startup velocity' },
  { name: 'Ledger', icon: DollarSign, desc: 'Finance — spending, subscriptions, budget' },
  { name: 'Clerk',  icon: FileText,   desc: 'Admin — documents, German bureaucracy, insurance' },
  { name: 'Scout',  icon: Search,     desc: 'Research — comparisons, courses, intelligence' },
];

const AGENT_COLORS: Record<string, string> = {
  Chief:  'text-[var(--v2-violet)]',
  Pulse:  'text-[#18E6D8]',
  Echo:   'text-[#8A3AFF]',
  Forge:  'text-[#38F2A8]',
  Ledger: 'text-[#F7A93B]',
  Clerk:  'text-[#3B82F6]',
  Scout:  'text-[var(--v2-muted)]',
};

export function AgentStatusPanel() {
  return (
    <section className="space-y-3">
      <div>
        <h2 className="text-sm font-semibold text-[var(--v2-text)]">Agents</h2>
        <p className="text-[12px] text-[var(--v2-muted)] mt-0.5">
          All agents active — routing happens automatically based on your query.
        </p>
      </div>
      <div className="space-y-2">
        {AGENTS.map(agent => {
          const Icon = agent.icon;
          return (
            <Panel key={agent.name} className="p-3 flex items-center gap-3">
              <div className="w-7 h-7 rounded-[8px] bg-[rgba(247,240,255,0.06)] flex items-center justify-center flex-shrink-0">
                <Icon size={14} className={AGENT_COLORS[agent.name]} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[13px] font-medium text-[var(--v2-text)]">{agent.name}</span>
                  <StatusDot severity="ok" size="xs" />
                </div>
                <p className="text-[11px] text-[var(--v2-subtle)] truncate">{agent.desc}</p>
              </div>
            </Panel>
          );
        })}
      </div>
    </section>
  );
}
