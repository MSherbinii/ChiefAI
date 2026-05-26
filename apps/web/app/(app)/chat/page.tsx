import { TopBar } from '@/components/layout/TopBar';
export default function ChatPage() {
  return (
    <>
      <TopBar title="Chat" />
      <main className="flex-1 overflow-y-auto p-4">
        <p className="text-[var(--v2-muted)] text-sm">Chat loading…</p>
      </main>
    </>
  );
}
