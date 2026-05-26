import { TopBar } from '@/components/layout/TopBar';
export default function TodayPage() {
  return (
    <>
      <TopBar title="Today" />
      <main className="flex-1 overflow-y-auto p-4">
        <p className="text-[var(--v2-muted)] text-sm">Today loading…</p>
      </main>
    </>
  );
}
