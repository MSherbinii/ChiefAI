// apps/web/app/(app)/replay/page.tsx
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { TopBar } from '@/components/layout/TopBar';
import { WeeklyReplay } from '@/components/replay/WeeklyReplay';

export default async function ReplayPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect('/login');

  const { data: checkIns } = await supabase
    .from('goal_check_ins')
    .select('*')
    .eq('user_id', user.id)
    .order('created_at', { ascending: false })
    .limit(20);

  const { data: scoreRow } = await supabase
    .from('momentum_scores')
    .select('total')
    .eq('user_id', user.id)
    .order('scored_at', { ascending: false })
    .limit(1)
    .maybeSingle();

  return (
    <>
      <TopBar title="Replay" />
      <main className="flex-1 overflow-y-auto p-4 max-w-2xl">
        <WeeklyReplay checkIns={checkIns ?? []} currentScore={scoreRow?.total ?? null} />
      </main>
    </>
  );
}
