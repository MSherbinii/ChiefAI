'use client';
import { useState } from 'react';
import { Activity, Briefcase, DollarSign, FileText } from 'lucide-react';
import { cn } from '@/lib/cn';
import { HealthDomain } from './HealthDomain';
import { WorkDomain } from './WorkDomain';
import { FinanceDomain } from './FinanceDomain';
import { AdminDomain } from './AdminDomain';

const TABS = [
  { id: 'health',  label: 'Health',  icon: Activity,    color: 'text-[#18E6D8]' },
  { id: 'work',    label: 'Work',    icon: Briefcase,   color: 'text-[#38F2A8]' },
  { id: 'finance', label: 'Finance', icon: DollarSign,  color: 'text-[#F7A93B]' },
  { id: 'admin',   label: 'Admin',   icon: FileText,    color: 'text-[#3B82F6]' },
] as const;

type TabId = typeof TABS[number]['id'];

interface Props {
  health: any;
  work: any;
  finance: any;
  admin: any;
}

export function DomainsDashboard({ health, work, finance, admin }: Props) {
  const [active, setActive] = useState<TabId>('health');

  return (
    <div className="flex flex-col h-full">
      {/* Tab bar */}
      <div className="flex border-b border-[var(--v2-border)] px-4">
        {TABS.map(tab => {
          const Icon = tab.icon;
          const isActive = active === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActive(tab.id)}
              className={cn(
                'flex items-center gap-2 px-4 py-3 text-[13px] font-medium border-b-2 transition-all -mb-px',
                isActive
                  ? `border-[var(--v2-violet)] ${tab.color}`
                  : 'border-transparent text-[var(--v2-muted)] hover:text-[var(--v2-text-dim)]'
              )}
            >
              <Icon size={14} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 max-w-3xl">
        {active === 'health'  && <HealthDomain  data={health} />}
        {active === 'work'    && <WorkDomain    data={work} />}
        {active === 'finance' && <FinanceDomain data={finance} />}
        {active === 'admin'   && <AdminDomain   data={admin} />}
      </div>
    </div>
  );
}
