import { cn } from '@/lib/cn';
import type { ChatMessage } from '@/store/chat';

interface MessageProps {
  message: ChatMessage;
}

export function Message({ message }: MessageProps) {
  const isUser = message.role === 'user';
  return (
    <div className={cn('flex gap-3', isUser && 'justify-end')}>
      {!isUser && (
        <div className="w-7 h-7 rounded-full bg-[linear-gradient(135deg,#2633D9,#8A3AFF)] flex-shrink-0 flex items-center justify-center mt-0.5">
          <span className="text-[10px] font-bold text-white">C</span>
        </div>
      )}
      <div
        className={cn(
          'max-w-[75%] px-3.5 py-2.5 rounded-[14px] text-sm',
          isUser
            ? 'bg-[rgba(138,58,255,0.15)] border border-[rgba(138,58,255,0.25)] text-[var(--v2-text)] rounded-tr-[4px]'
            : 'border border-[rgba(247,240,255,0.10)] [background:linear-gradient(180deg,rgba(18,24,34,0.98),rgba(11,15,22,0.98))] text-[var(--v2-text-dim)] rounded-tl-[4px]'
        )}
      >
        {!isUser && message.agent && (
          <div className="text-[10px] text-[var(--v2-violet)] uppercase tracking-[0.08em] mb-1">
            via {message.agent}
          </div>
        )}
        <p className="leading-relaxed whitespace-pre-wrap">{message.content}</p>
        <div className="text-[10px] text-[var(--v2-subtle)] mt-1.5">
          {message.createdAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </div>
  );
}
