'use client';
import { useState } from 'react';
import { Button } from '@/components/design-system';
import { RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

interface ConnectorSyncButtonProps {
  connector: string; // 'google', 'github', 'whoop', 'imap_uni'
}

export function ConnectorSyncButton({ connector }: ConnectorSyncButtonProps) {
  const [loading, setLoading] = useState(false);

  async function handleSync() {
    setLoading(true);
    try {
      const res = await fetch('/api/connectors/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ connector }),
      });
      if (res.ok) {
        toast.success(`${connector} sync started`);
      } else {
        toast.error('Sync failed');
      }
    } catch {
      toast.error('Sync failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Button variant="ghost" size="xs" loading={loading} onClick={handleSync}>
      <RefreshCw size={11} />
      Sync
    </Button>
  );
}
