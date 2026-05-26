import { TopBar } from '@/components/layout/TopBar';
export default function SettingsPage() {
  return (
    <>
      <TopBar title="Settings" />
      <main className="flex-1 overflow-y-auto p-4">
        <p className="text-[var(--v2-muted)] text-sm">Settings loading…</p>
      </main>
    </>
  );
}
