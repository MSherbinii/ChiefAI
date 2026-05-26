import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { TopBar } from '@/components/layout/TopBar';
import { DomainsDashboard } from '@/components/domains/DomainsDashboard';

export default async function DomainsPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect('/login');

  const cutoff7d = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
  const cutoff30d = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();

  // Health data
  const [{ data: recoveries }, { data: sleeps }, { data: workouts }] = await Promise.all([
    supabase.from('lg_health').select('value, recorded_at').eq('user_id', user.id).eq('metric', 'recovery').gte('recorded_at', cutoff7d).order('recorded_at', { ascending: false }),
    supabase.from('lg_health').select('value, recorded_at').eq('user_id', user.id).eq('metric', 'sleep').gte('recorded_at', cutoff7d).order('recorded_at', { ascending: false }),
    supabase.from('lg_health').select('value, recorded_at').eq('user_id', user.id).eq('metric', 'workout').gte('recorded_at', cutoff7d).order('recorded_at', { ascending: false }),
  ]);

  // Work data
  const [{ data: commits }, { data: projects }, { data: staleComms }] = await Promise.all([
    supabase.from('lg_health').select('value, recorded_at').eq('user_id', user.id).eq('metric', 'github_commit').gte('recorded_at', cutoff7d).order('recorded_at', { ascending: false }),
    supabase.from('lg_projects').select('name, type, status, deadline').eq('user_id', user.id).eq('status', 'active'),
    supabase.from('lg_communications').select('subject, participants, channel, last_message_at, staleness_days').eq('user_id', user.id).eq('status', 'active').lte('last_message_at', cutoff7d).order('last_message_at', { ascending: true }).limit(10),
  ]);

  // Finance data
  const [{ data: transactions }, { data: subscriptions }] = await Promise.all([
    supabase.from('lg_finance').select('amount_cents, category, description, transaction_at').eq('user_id', user.id).eq('type', 'transaction').gte('transaction_at', cutoff30d).order('transaction_at', { ascending: false }).limit(20),
    supabase.from('lg_finance').select('description, amount_cents, recurring_period, last_used_at').eq('user_id', user.id).eq('is_subscription', true),
  ]);

  // Admin data
  const [{ data: documents }, { data: pendingQueue }] = await Promise.all([
    supabase.from('lg_documents').select('type, title, expires_at').eq('user_id', user.id).order('created_at', { ascending: false }).limit(10),
    supabase.from('approval_queue').select('agent, title, risk_level, created_at').eq('user_id', user.id).eq('status', 'pending').order('created_at', { ascending: false }).limit(5),
  ]);

  return (
    <>
      <TopBar title="Domains" />
      <main className="flex-1 overflow-y-auto">
        <DomainsDashboard
          health={{ recoveries: recoveries ?? [], sleeps: sleeps ?? [], workouts: workouts ?? [] }}
          work={{ commits: commits ?? [], projects: projects ?? [], staleComms: staleComms ?? [] }}
          finance={{ transactions: transactions ?? [], subscriptions: subscriptions ?? [] }}
          admin={{ documents: documents ?? [], pendingQueue: pendingQueue ?? [] }}
        />
      </main>
    </>
  );
}
