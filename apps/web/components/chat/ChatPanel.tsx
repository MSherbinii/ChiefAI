'use client';
import { useEffect, useRef } from 'react';
import { Message } from './Message';
import { ChatInput } from './ChatInput';
import { useChatStore } from '@/store/chat';

export function ChatPanel() {
  const { messages, isLoading, addMessage, setLoading } = useChatStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function handleSend(content: string) {
    addMessage({ role: 'user', content });
    setLoading(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content, history: messages.slice(-10) }),
      });
      const data = await res.json();
      addMessage({ role: 'assistant', content: data.reply, agent: data.agent });
    } catch {
      addMessage({
        role: 'assistant',
        content: "I'm having trouble connecting right now. Try again in a moment.",
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-3 pb-12">
            <div className="w-12 h-12 rounded-full bg-[linear-gradient(135deg,#2633D9,#8A3AFF)] flex items-center justify-center">
              <span className="text-lg font-bold text-white">C</span>
            </div>
            <div>
              <p className="text-sm font-medium text-[var(--v2-text)]">Hey, I&apos;m Chief.</p>
              <p className="text-[13px] text-[var(--v2-muted)] mt-1">
                Ask me anything about your health, finances, work, or admin.
              </p>
            </div>
          </div>
        )}
        {messages.map(msg => <Message key={msg.id} message={msg} />)}
        {isLoading && (
          <div className="flex gap-3">
            <div className="w-7 h-7 rounded-full bg-[linear-gradient(135deg,#2633D9,#8A3AFF)] flex-shrink-0 flex items-center justify-center">
              <span className="text-[10px] font-bold text-white">C</span>
            </div>
            <div className="px-3.5 py-2.5 rounded-[14px] rounded-tl-[4px] border border-[rgba(247,240,255,0.10)] [background:linear-gradient(180deg,rgba(18,24,34,0.98),rgba(11,15,22,0.98))]">
              <div className="flex gap-1 items-center h-5">
                {[0, 0.15, 0.3].map(delay => (
                  <div
                    key={delay}
                    className="w-1.5 h-1.5 rounded-full bg-[var(--v2-violet)]"
                    style={{ animation: `chief-pulse 1.2s ease-in-out ${delay}s infinite` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <ChatInput onSend={handleSend} disabled={isLoading} />
    </div>
  );
}
