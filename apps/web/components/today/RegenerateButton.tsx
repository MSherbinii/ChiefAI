'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { RefreshCw } from 'lucide-react';
import { Button } from '@/components/design-system';
import { toast } from 'sonner';

export function RegenerateButton() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function handleRegenerate() {
    setLoading(true);
    try {
      await fetch('/api/agent/score', { method: 'POST' });
      const res = await fetch('/api/agent/brief', { method: 'POST' });
      if (res.ok) {
        toast.success('Brief regenerated');
        router.refresh();
      } else {
        toast.error('Regeneration failed');
      }
    } catch {
      toast.error('Agent service unavailable');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Button variant="ghost" size="xs" loading={loading} onClick={handleRegenerate}>
      {!loading && <RefreshCw size={11} />}
      Refresh brief
    </Button>
  );
}
