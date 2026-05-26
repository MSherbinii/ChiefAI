'use client';
import { Bell } from 'lucide-react';
import { Button } from '@/components/design-system';
import { createClient } from '@/lib/supabase/client';
import { useRouter } from 'next/navigation';

interface TopBarProps {
  title: string;
  momentumScore?: number;
}

export function TopBar({ title, momentumScore }: TopBarProps) {
  const router = useRouter();
  const supabase = createClient();

  async function signOut() {
    await supabase.auth.signOut();
    router.push('/login');
  }

  return (
    <header className="h-12 flex items-center justify-between px-4 border-b border-[var(--v2-border)] bg-[rgba(8,10,14,0.80)] backdrop-blur-sm flex-shrink-0">
      <h1 className="text-sm font-semibold text-[var(--v2-text)]">{title}</h1>
      <div className="flex items-center gap-3">
        {momentumScore !== undefined && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[rgba(138,58,255,0.12)] border border-[rgba(138,58,255,0.20)]">
            <div className="w-1.5 h-1.5 rounded-full bg-[var(--v2-violet)]" />
            <span className="text-[12px] font-semibold text-[var(--v2-text)]">{momentumScore}</span>
            <span className="text-[11px] text-[var(--v2-muted)]">momentum</span>
          </div>
        )}
        <Button variant="ghost" size="xs" className="w-8 h-8 p-0 justify-center">
          <Bell size={14} />
        </Button>
        <Button variant="ghost" size="xs" onClick={signOut}>
          Sign out
        </Button>
      </div>
    </header>
  );
}
