import { TopBar } from '@/components/layout/TopBar';
import { Panel } from '@/components/design-system';
import { LayoutGrid } from 'lucide-react';

export default function DomainsPage() {
  return (
    <>
      <TopBar title="Domains" />
      <main className="flex-1 overflow-y-auto p-4 max-w-3xl">
        <div className="flex flex-col items-center justify-center h-64 text-center space-y-3">
          <LayoutGrid size={32} className="text-[var(--v2-violet)] opacity-40" />
          <p className="text-sm font-medium text-[var(--v2-text)]">Domains coming soon.</p>
          <p className="text-[13px] text-[var(--v2-muted)] max-w-xs">
            Drill into Health, Finance, Work, and Admin with dedicated domain views.
            Connect your sources first to populate data.
          </p>
        </div>
      </main>
    </>
  );
}
