import { cn } from '@/lib/cn';
import type { ChatMessage } from '@/store/chat';
import { Zap, Activity, Mail, GitBranch, DollarSign, FileText, Search } from 'lucide-react';

// Agent → color + icon mapping
const AGENT_CONFIG: Record<string, { color: string; bg: string; icon: React.ElementType; label: string }> = {
  Pulse:  { color: 'text-[#18E6D8]', bg: 'bg-[rgba(24,230,216,0.12)] border-[rgba(24,230,216,0.25)]', icon: Activity, label: 'Pulse' },
  Echo:   { color: 'text-[#8A3AFF]', bg: 'bg-[rgba(138,58,255,0.12)] border-[rgba(138,58,255,0.25)]', icon: Mail,     label: 'Echo' },
  Forge:  { color: 'text-[#38F2A8]', bg: 'bg-[rgba(56,242,168,0.12)] border-[rgba(56,242,168,0.25)]', icon: GitBranch, label: 'Forge' },
  Ledger: { color: 'text-[#F7A93B]', bg: 'bg-[rgba(247,169,59,0.12)] border-[rgba(247,169,59,0.25)]', icon: DollarSign, label: 'Ledger' },
  Clerk:  { color: 'text-[#3B82F6]', bg: 'bg-[rgba(59,130,246,0.12)] border-[rgba(59,130,246,0.25)]', icon: FileText,  label: 'Clerk' },
  Scout:  { color: 'text-[var(--v2-muted)]', bg: 'bg-[rgba(247,240,255,0.08)] border-[rgba(247,240,255,0.15)]', icon: Search, label: 'Scout' },
  Chief:  { color: 'text-[var(--v2-violet)]', bg: 'bg-[rgba(138,58,255,0.08)] border-[rgba(138,58,255,0.18)]', icon: Zap, label: 'Chief' },
};

interface MessageProps {
  message: ChatMessage;
}

export function Message({ message }: MessageProps) {
  const isUser = message.role === 'user';
  const agentCfg = message.agent ? AGENT_CONFIG[message.agent] ?? AGENT_CONFIG['Chief'] : null;
  const AgentIcon = agentCfg?.icon ?? Zap;

  return (
    <div className={cn('flex gap-3 group', isUser && 'justify-end')}>
      {!isUser && agentCfg && (
        <div className={cn(
          'w-7 h-7 rounded-full border flex-shrink-0 flex items-center justify-center mt-0.5',
          agentCfg.bg
        )}>
          <AgentIcon size={13} className={agentCfg.color} />
        </div>
      )}
      {!isUser && !agentCfg && (
        <div className="w-7 h-7 rounded-full bg-[linear-gradient(135deg,#2633D9,#8A3AFF)] flex-shrink-0 flex items-center justify-center mt-0.5">
          <Zap size={13} className="text-white" />
        </div>
      )}

      <div className={cn(
        'max-w-[78%] space-y-1.5',
        isUser && 'items-end flex flex-col'
      )}>
        {!isUser && message.agent && agentCfg && (
          <span className={cn('text-[10px] font-semibold uppercase tracking-[0.1em]', agentCfg.color)}>
            {agentCfg.label}
          </span>
        )}
        <div className={cn(
          'px-3.5 py-2.5 rounded-[14px] text-sm leading-relaxed',
          isUser
            ? 'bg-[rgba(138,58,255,0.15)] border border-[rgba(138,58,255,0.25)] text-[var(--v2-text)] rounded-tr-[4px]'
            : 'border border-[rgba(247,240,255,0.10)] [background:linear-gradient(180deg,rgba(18,24,34,0.98),rgba(11,15,22,0.98))] text-[var(--v2-text-dim)] rounded-tl-[4px]'
        )}>
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        <div className={cn(
          'text-[10px] text-[var(--v2-subtle)] opacity-0 group-hover:opacity-100 transition-opacity',
          isUser && 'text-right'
        )}>
          {message.createdAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </div>
  );
}
