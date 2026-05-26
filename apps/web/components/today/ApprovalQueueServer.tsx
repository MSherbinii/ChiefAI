'use client';
import { useState } from 'react';
import { ApprovalQueue, type QueueItem } from './ApprovalQueue';
import { toast } from 'sonner';

interface QueueRow {
  id: string;
  agent: string;
  title: string;
  description: string | null;
  risk_level: 'auto' | 'notify' | 'approve' | 'confirm';
  context_capsule: Record<string, unknown> | null;
}

function mapRow(i: QueueRow): QueueItem {
  const capsule = i.context_capsule as any;
  return {
    id: i.id,
    agent: i.agent,
    title: i.title,
    description: i.description ?? '',
    riskLevel: i.risk_level,
    contextCapsule: capsule ? {
      sources: capsule.sources ?? [],
      reasoning: capsule.reasoning ?? '',
      confidence: capsule.confidence ?? 'MEDIUM',
    } : undefined,
    autoApproveSuggested: capsule?.auto_approve_suggested ?? false,
  };
}

export function ApprovalQueueServer({ items }: { items: QueueRow[] }) {
  const [localItems, setLocalItems] = useState<QueueItem[]>(items.map(mapRow));

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

  async function handleAutoApprove(id: string) {
    const item = localItems.find(i => i.id === id);
    await fetch('/api/queue/auto-approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, agent: item?.agent }),
    });
    toast.success('Auto-approve enabled for this action type.');
  }

  return (
    <ApprovalQueue
      items={localItems}
      onApprove={handleApprove}
      onReject={handleReject}
      onEnableAutoApprove={handleAutoApprove}
    />
  );
}
