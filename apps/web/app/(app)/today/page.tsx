// apps/web/app/(app)/today/page.tsx
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { TopBar } from '@/components/layout/TopBar';
import { ConnectGate } from '@/components/today/ConnectGate';
import { MorningBriefReal, type AiBriefSection } from '@/components/today/MorningBriefReal';
import { MomentumScore } from '@/components/today/MomentumScore';
import { ApprovalQueueServer } from '@/components/today/ApprovalQueueServer';
import { LifeDebt } from '@/components/today/LifeDebt';

export default async function TodayPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect('/login');

  // Gate: at least one connector must be live
  const { data: tokens } = await supabase
    .from('connector_tokens')
    .select('connector, sync_status')
    .eq('user_id', user.id)
    .in('sync_status', ['ok', 'syncing']);

  const hasLiveConnector = (tokens ?? []).length > 0;

  // Latest momentum score
  const { data: scoreRow } = await supabase
    .from('momentum_scores')
    .select('*')
    .eq('user_id', user.id)
    .order('scored_at', { ascending: false })
    .limit(1)
    .maybeSingle();

  // Latest AI-generated brief for today
  const today = new Date().toISOString().slice(0, 10);
  const { data: brief } = await supabase
    .from('briefs')
    .select('*')
    .eq('user_id', user.id)
    .eq('brief_date', today)
    .eq('type', 'morning')
    .maybeSingle();

  // Pending approval queue
  const { data: queueItems } = await supabase
    .from('approval_queue')
    .select('id, agent, title, description, risk_level, context_capsule')
    .eq('user_id', user.id)
    .eq('status', 'pending')
    .order('created_at', { ascending: false })
    .limit(10);

  const domains = scoreRow ? [
    { label: 'Body',       value: scoreRow.body ?? 0,       color: '#18E6D8' },
    { label: 'Money',      value: scoreRow.money ?? 0,      color: '#F7A93B' },
    { label: 'Work',       value: scoreRow.work ?? 0,       color: '#8A3AFF' },
    { label: 'Admin',      value: scoreRow.admin ?? 0,      color: '#38F2A8' },
    { label: 'Discipline', value: scoreRow.discipline ?? 0, color: '#3B82F6' },
  ] : [];

  const greeting = brief?.greeting ?? (() => {
    const hour = new Date().getHours();
    return hour < 12 ? 'Good morning.' : hour < 18 ? 'Good afternoon.' : 'Good evening.';
  })();

  const sections: AiBriefSection[] = (brief?.sections as AiBriefSection[]) ?? [];
  const lifeDebt = brief?.life_debt as { total: number; items: { domain: string; count: number; description: string }[] } | null;
  const bestMove = (brief as any)?.best_move as string | undefined;
  const patterns = (brief as any)?.patterns as string[] | undefined;

  const queueRows = (queueItems ?? []).map(i => ({
    id: i.id as string,
    agent: i.agent as string,
    title: i.title as string,
    description: (i.description as string) ?? '',
    risk_level: i.risk_level as 'auto' | 'notify' | 'approve' | 'confirm',
  }));

  return (
    <>
      <TopBar title="Today" momentumScore={scoreRow?.total} />
      <main className="flex-1 overflow-y-auto p-4 max-w-3xl">
        {!hasLiveConnector ? (
          <ConnectGate />
        ) : (
          <div className="space-y-5">
            {scoreRow && <MomentumScore total={scoreRow.total} domains={domains} />}
            {lifeDebt && lifeDebt.total > 0 && (
              <LifeDebt total={lifeDebt.total} items={lifeDebt.items} />
            )}
            <MorningBriefReal
              greeting={greeting}
              sections={sections}
              bestMove={bestMove}
              patterns={patterns}
            />
            <ApprovalQueueServer items={queueRows} />
          </div>
        )}
      </main>
    </>
  );
}
