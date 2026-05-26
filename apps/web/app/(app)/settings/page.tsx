import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { getConnectorStates } from '@/lib/connectors';
import { TopBar } from '@/components/layout/TopBar';
import { SettingsConnectors } from '@/components/settings/SettingsConnectors';
import { AgentStatusPanel } from '@/components/settings/AgentStatusPanel';
import { DocumentUpload } from '@/components/settings/DocumentUpload';

export default async function SettingsPage({
  searchParams,
}: {
  searchParams: Promise<{ connected?: string; error?: string }>;
}) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect('/login');

  const [connectorStates, profileResult] = await Promise.all([
    getConnectorStates(user.id),
    supabase.from('profiles').select('display_name, timezone').eq('id', user.id).maybeSingle(),
  ]);

  const profile = profileResult.data;
  const params = await searchParams;

  const displayName = profile?.display_name ?? user.email?.split('@')[0] ?? 'U';
  const avatarLetter = displayName[0].toUpperCase();

  return (
    <>
      <TopBar title="Settings" />
      <main className="flex-1 overflow-y-auto p-4 max-w-2xl space-y-6">
        {params.connected && (
          <div className="px-4 py-2.5 rounded-[10px] bg-[rgba(56,242,168,0.08)] border border-[rgba(56,242,168,0.20)] text-[13px] text-[var(--v2-ok)]">
            ✓ {params.connected} connected successfully.
          </div>
        )}
        {params.error && (
          <div className="px-4 py-2.5 rounded-[10px] bg-[rgba(255,79,109,0.08)] border border-[rgba(255,79,109,0.20)] text-[13px] text-[var(--v2-crit)]">
            Connection failed: {params.error.replace(/_/g, ' ')}
          </div>
        )}

        {/* Profile section */}
        <section className="space-y-3">
          <h2 className="text-sm font-semibold text-[var(--v2-text)]">Profile</h2>
          <div className="rounded-[14px] border border-[rgba(247,240,255,0.10)] [background:linear-gradient(180deg,rgba(18,24,34,0.98),rgba(11,15,22,0.98))] p-4 flex items-center justify-between">
            <div className="space-y-0.5">
              <p className="text-sm font-semibold text-[var(--v2-text)]">{displayName}</p>
              <p className="text-[12px] text-[var(--v2-muted)]">{user.email}</p>
              {profile?.timezone && (
                <p className="text-[11px] text-[var(--v2-subtle)]">{profile.timezone}</p>
              )}
            </div>
            <div className="w-10 h-10 rounded-full bg-[linear-gradient(135deg,#2633D9,#8A3AFF)] flex items-center justify-center text-white text-sm font-bold">
              {avatarLetter}
            </div>
          </div>
        </section>

        <SettingsConnectors states={connectorStates} />

        <section className="space-y-3">
          <h2 className="text-sm font-semibold text-[var(--v2-text)]">Documents</h2>
          <div className="rounded-[14px] border border-[rgba(247,240,255,0.10)] [background:linear-gradient(180deg,rgba(18,24,34,0.98),rgba(11,15,22,0.98))] p-4">
            <DocumentUpload />
          </div>
        </section>

        <AgentStatusPanel />
      </main>
    </>
  );
}
