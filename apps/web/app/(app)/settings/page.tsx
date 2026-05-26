import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { getConnectorStates } from '@/lib/connectors';
import { TopBar } from '@/components/layout/TopBar';
import { SettingsConnectors } from '@/components/settings/SettingsConnectors';

export default async function SettingsPage({
  searchParams,
}: {
  searchParams: Promise<{ connected?: string; error?: string }>;
}) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect('/login');

  const connectorStates = await getConnectorStates(user.id);
  const params = await searchParams;

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
        <SettingsConnectors states={connectorStates} />
      </main>
    </>
  );
}
