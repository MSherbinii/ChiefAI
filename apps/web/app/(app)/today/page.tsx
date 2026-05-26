import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { TopBar } from '@/components/layout/TopBar';
import { ConnectGate } from '@/components/today/ConnectGate';
import { MorningBriefReal } from '@/components/today/MorningBriefReal';
import { MomentumScore } from '@/components/today/MomentumScore';
import { ApprovalQueueServer } from '@/components/today/ApprovalQueueServer';
import { Activity, Briefcase, FileText } from 'lucide-react';

export default async function TodayPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect('/login');

  // Check if any connector is live
  const { data: tokens } = await supabase
    .from('connector_tokens')
    .select('connector, sync_status')
    .eq('user_id', user.id)
    .in('sync_status', ['ok', 'syncing']);

  const hasLiveConnector = (tokens ?? []).length > 0;

  // Fetch latest momentum score
  const { data: scoreRow } = await supabase
    .from('momentum_scores')
    .select('*')
    .eq('user_id', user.id)
    .order('scored_at', { ascending: false })
    .limit(1)
    .maybeSingle();

  // Fetch pending approval queue items
  const { data: queueItems } = await supabase
    .from('approval_queue')
    .select('id, agent, title, description, risk_level')
    .eq('user_id', user.id)
    .eq('status', 'pending')
    .order('created_at', { ascending: false })
    .limit(10);

  // Build brief sections from real data
  const briefSections: Array<{
    domain: 'body' | 'work' | 'admin';
    label: string;
    agent: string;
    icon: typeof Activity;
    headline: string;
    detail: string;
    status: 'ok' | 'med' | 'high' | 'crit';
  }> = [];

  if (hasLiveConnector) {
    // Body: latest WHOOP recovery
    const { data: latestRecovery } = await supabase
      .from('lg_health')
      .select('value, recorded_at')
      .eq('user_id', user.id)
      .eq('metric', 'recovery')
      .order('recorded_at', { ascending: false })
      .limit(1)
      .maybeSingle();

    if (latestRecovery) {
      const val = latestRecovery.value as Record<string, number> | null;
      const score = val?.recovery_score ?? 0;
      briefSections.push({
        domain: 'body',
        label: 'Body',
        agent: 'Pulse',
        icon: Activity,
        headline: `Recovery ${score}%`,
        detail: score >= 67
          ? "You're in the green. Train as planned."
          : score >= 34
          ? 'Moderate recovery. Consider lighter intensity today.'
          : 'Low recovery. Rest or zone 2 recommended.',
        status: score >= 67 ? 'ok' : score >= 34 ? 'med' : 'high',
      });
    }

    // Work: stale communications
    const { data: staleComms } = await supabase
      .from('lg_communications')
      .select('subject, participants, last_message_at, staleness_days')
      .eq('user_id', user.id)
      .eq('status', 'active')
      .gte('staleness_days', 3)
      .order('staleness_days', { ascending: false })
      .limit(3);

    if (staleComms && staleComms.length > 0) {
      const top = staleComms[0];
      briefSections.push({
        domain: 'work',
        label: 'Work',
        agent: 'Echo + Forge',
        icon: Briefcase,
        headline: `${staleComms.length} thread${staleComms.length > 1 ? 's' : ''} need attention`,
        detail: `"${((top.subject as string) ?? '').slice(0, 60)}" — ${top.staleness_days} days without reply.`,
        status: staleComms.some(c => ((c.staleness_days as number) ?? 0) >= 7) ? 'high' : 'med',
      });
    }

    // Admin: pending queue items
    if (queueItems && queueItems.length > 0) {
      briefSections.push({
        domain: 'admin',
        label: 'Admin',
        agent: 'Clerk',
        icon: FileText,
        headline: `${queueItems.length} item${queueItems.length > 1 ? 's' : ''} in queue`,
        detail: queueItems[0].title as string,
        status: 'med',
      });
    }
  }

  const domains = scoreRow ? [
    { label: 'Body',       value: (scoreRow.body as number) ?? 0,       color: '#18E6D8' },
    { label: 'Money',      value: (scoreRow.money as number) ?? 0,      color: '#F7A93B' },
    { label: 'Work',       value: (scoreRow.work as number) ?? 0,       color: '#8A3AFF' },
    { label: 'Admin',      value: (scoreRow.admin as number) ?? 0,      color: '#38F2A8' },
    { label: 'Discipline', value: (scoreRow.discipline as number) ?? 0, color: '#3B82F6' },
  ] : [];

  const hour = new Date().getHours();
  const greeting =
    hour < 12 ? 'Good morning, Mohamed.' :
    hour < 18 ? 'Good afternoon, Mohamed.' :
                'Good evening, Mohamed.';

  const queueRows = (queueItems ?? []).map(i => ({
    id: i.id as string,
    agent: i.agent as string,
    title: i.title as string,
    description: (i.description as string) ?? '',
    risk_level: i.risk_level as 'auto' | 'notify' | 'approve' | 'confirm',
  }));

  return (
    <>
      <TopBar title="Today" momentumScore={scoreRow?.total as number | undefined} />
      <main className="flex-1 overflow-y-auto p-4 max-w-3xl">
        {!hasLiveConnector ? (
          <ConnectGate />
        ) : (
          <div className="space-y-5">
            {scoreRow && (
              <MomentumScore total={scoreRow.total as number} domains={domains} />
            )}
            <MorningBriefReal sections={briefSections} greeting={greeting} />
            <ApprovalQueueServer items={queueRows} />
          </div>
        )}
      </main>
    </>
  );
}
