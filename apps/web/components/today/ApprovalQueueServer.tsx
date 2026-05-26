'use client';
import { useState } from 'react';
import { ApprovalQueue, type QueueItem } from './ApprovalQueue';
import { toast } from 'sonner';

interface QueueRow {
  id: string;
  agent: string;
  title: string;
  description: string;
  risk_level: 'auto' | 'notify' | 'approve' | 'confirm';
}

export function ApprovalQueueServer({ items }: { items: QueueRow[] }) {
  const [localItems, setLocalItems] = useState<QueueItem[]>(
    items.map(i => ({
      id: i.id,
      agent: i.agent,
      title: i.title,
      description: i.description ?? '',
      riskLevel: i.risk_level,
    }))
  );

  async function handleApprove(id: string) {
    const item = localItems.find(i => i.id === id);
    setLocalItems(prev => prev.filter(i => i.id !== id));
    await fetch('/api/queue/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id }),
    });
    toast.success(`Approved: ${item?.title}`);
  }

  async function handleReject(id: string) {
    const item = localItems.find(i => i.id === id);
    setLocalItems(prev => prev.filter(i => i.id !== id));
    await fetch('/api/queue/reject', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id }),
    });
    toast(`Skipped: ${item?.title}`);
  }

  return (
    <ApprovalQueue
      items={localItems}
      onApprove={handleApprove}
      onReject={handleReject}
    />
  );
}
