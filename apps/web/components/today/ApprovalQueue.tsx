'use client';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Panel, Button, StatusDot } from '@/components/design-system';
import { CheckCircle, XCircle, ChevronDown, Zap } from 'lucide-react';

export interface QueueItem {
  id: string;
  agent: string;
  title: string;
  description: string;
  riskLevel: 'auto' | 'notify' | 'approve' | 'confirm';
  contextCapsule?: {
    sources?: string[];
    reasoning?: string;
    confidence?: 'HIGH' | 'MEDIUM' | 'LOW';
  };
  autoApproveSuggested?: boolean;
}

interface ApprovalQueueProps {
  items: QueueItem[];
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  onEnableAutoApprove?: (id: string) => void;
}

const RISK_SEVERITY: Record<QueueItem['riskLevel'], 'ok' | 'info' | 'med' | 'high'> = {
  auto:    'ok',
  notify:  'info',
  approve: 'med',
  confirm: 'high',
};

const RISK_LABELS: Record<QueueItem['riskLevel'], string> = {
  auto:    'auto',
  notify:  'notify',
  approve: 'approval',
  confirm: 'confirm',
};

export function ApprovalQueue({ items, onApprove, onReject, onEnableAutoApprove }: ApprovalQueueProps) {
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
            <Panel className="p-3 space-y-2">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-2 flex-1 min-w-0">
                  <StatusDot severity={RISK_SEVERITY[item.riskLevel]} size="xs" className="mt-1 flex-shrink-0" />
                  <div className="min-w-0 space-y-0.5">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium text-[var(--v2-text)] truncate">{item.title}</span>
                      <span className="text-[10px] text-[var(--v2-subtle)] flex-shrink-0">[{item.agent}]</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded-[4px] bg-[rgba(247,240,255,0.06)] text-[var(--v2-subtle)]">
                        {RISK_LABELS[item.riskLevel]}
                      </span>
                      {item.autoApproveSuggested && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-[4px] bg-[rgba(56,242,168,0.10)] text-[var(--v2-ok)] flex items-center gap-1">
                          <Zap size={9} />
                          auto-approve available
                        </span>
                      )}
                    </div>
                    {item.description && (
                      <p className="text-[12px] text-[var(--v2-muted)]">{item.description}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  {item.contextCapsule && (
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
                  )}
                  <Button variant="ghost" size="xs" onClick={() => onReject(item.id)}>
                    <XCircle size={13} className="text-[var(--v2-crit)]" />
                  </Button>
                  <Button variant="solid" size="xs" onClick={() => onApprove(item.id)}>
                    <CheckCircle size={13} />
                    Approve
                  </Button>
                </div>
              </div>

              {expanded === item.id && item.contextCapsule && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="border-t border-[var(--v2-border)] pt-2 space-y-1.5"
                >
                  <p className="text-[10px] uppercase tracking-[0.08em] text-[var(--v2-subtle)]">Context capsule</p>
                  {item.contextCapsule.sources && item.contextCapsule.sources.length > 0 && (
                    <div className="space-y-0.5">
                      {item.contextCapsule.sources.map((s, i) => (
                        <p key={i} className="text-[11px] text-[var(--v2-muted)] font-mono">├─ {s}</p>
                      ))}
                    </div>
                  )}
                  {item.contextCapsule.reasoning && (
                    <p className="text-[12px] text-[var(--v2-text-dim)]">{item.contextCapsule.reasoning}</p>
                  )}
                  {item.contextCapsule.confidence && (
                    <p className="text-[11px] text-[var(--v2-subtle)]">
                      Confidence: <span className="text-[var(--v2-text-dim)]">{item.contextCapsule.confidence}</span>
                    </p>
                  )}
                  {item.autoApproveSuggested && onEnableAutoApprove && (
                    <Button variant="outline" size="xs" onClick={() => onEnableAutoApprove(item.id)}>
                      <Zap size={10} />
                      Enable auto-approve for this action
                    </Button>
                  )}
                </motion.div>
              )}
            </Panel>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
