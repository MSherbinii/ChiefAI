'use client';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Panel, Button, StatusDot } from '@/components/design-system';
import { CheckCircle, XCircle, ChevronDown } from 'lucide-react';

export interface QueueItem {
  id: string;
  agent: string;
  title: string;
  description: string;
  riskLevel: 'auto' | 'notify' | 'approve' | 'confirm';
}

interface ApprovalQueueProps {
  items: QueueItem[];
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}

const RISK_SEVERITY: Record<QueueItem['riskLevel'], 'ok' | 'info' | 'med' | 'high'> = {
  auto:    'ok',
  notify:  'info',
  approve: 'med',
  confirm: 'high',
};

export function ApprovalQueue({ items, onApprove, onReject }: ApprovalQueueProps) {
  const [expanded, setExpanded] = useState<string | null>(null);

  if (items.length === 0) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-[12px] uppercase tracking-[0.08em] font-semibold text-[var(--v2-muted)]">
        Queue — {items.length} item{items.length !== 1 ? 's' : ''}
      </h3>
      <AnimatePresence initial={false}>
        {items.map(item => (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, x: 40, transition: { duration: 0.2 } }}
            transition={{ duration: 0.25 }}
          >
            <Panel className="p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-2 flex-1 min-w-0">
                  <StatusDot severity={RISK_SEVERITY[item.riskLevel]} size="xs" className="mt-1 flex-shrink-0" />
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-[var(--v2-text)] truncate">{item.title}</span>
                      <span className="text-[10px] text-[var(--v2-subtle)] flex-shrink-0">[{item.agent}]</span>
                    </div>
                    {expanded === item.id && (
                      <p className="text-[12px] text-[var(--v2-muted)] mt-1">{item.description}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  <Button
                    variant="ghost"
                    size="xs"
                    onClick={() => setExpanded(expanded === item.id ? null : item.id)}
                  >
                    <ChevronDown
                      size={12}
                      className={expanded === item.id ? 'rotate-180 transition-transform' : 'transition-transform'}
                    />
                  </Button>
                  <Button variant="ghost" size="xs" onClick={() => onReject(item.id)}>
                    <XCircle size={13} className="text-[var(--v2-crit)]" />
                  </Button>
                  <Button variant="solid" size="xs" onClick={() => onApprove(item.id)}>
                    <CheckCircle size={13} />
                    Approve
                  </Button>
                </div>
              </div>
            </Panel>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
