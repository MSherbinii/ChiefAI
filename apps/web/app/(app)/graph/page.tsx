import { TopBar } from '@/components/layout/TopBar';
import { GitBranch } from 'lucide-react';

export default function GraphPage() {
  return (
    <>
      <TopBar title="Life Graph" />
      <main className="flex-1 overflow-y-auto p-4 max-w-3xl">
        <div className="flex flex-col items-center justify-center h-64 text-center space-y-3">
          <GitBranch size={32} className="text-[var(--v2-violet)] opacity-40" />
          <p className="text-sm font-medium text-[var(--v2-text)]">Life Graph coming soon.</p>
          <p className="text-[13px] text-[var(--v2-muted)] max-w-xs">
            Your knowledge graph — people, projects, facts and relationships — visualized.
            Entities are being extracted from your connected sources.
          </p>
        </div>
      </main>
    </>
  );
}
