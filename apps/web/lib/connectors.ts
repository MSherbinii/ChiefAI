import { createClient } from '@/lib/supabase/server';

export type ConnectorStatus = 'connected' | 'disconnected' | 'error' | 'syncing';

export interface ConnectorState {
  connector: string;
  status: ConnectorStatus;
  lastSynced: string | null;
  extra: Record<string, string> | null;
  errorMessage: string | null;
}

export async function getConnectorStates(userId: string): Promise<Record<string, ConnectorState>> {
  const supabase = await createClient();
  const { data } = await supabase
    .from('connector_tokens')
    .select('connector, sync_status, last_synced_at, extra, error_message')
    .eq('user_id', userId);

  const result: Record<string, ConnectorState> = {};
  for (const row of data ?? []) {
    result[row.connector] = {
      connector: row.connector,
      status: row.sync_status === 'ok' ? 'connected'
             : row.sync_status === 'error' ? 'error'
             : row.sync_status === 'syncing' ? 'syncing'
             : 'disconnected',
      lastSynced: row.last_synced_at,
      extra: row.extra,
      errorMessage: row.error_message,
    };
  }
  return result;
}
