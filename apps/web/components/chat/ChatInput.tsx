'use client';
import { useState, useRef, type KeyboardEvent } from 'react';
import { Button } from '@/components/design-system';
import { SendHorizontal } from 'lucide-react';

interface ChatInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function submit() {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function handleInput(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setValue(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  }

  return (
    <div className="p-3 border-t border-[var(--v2-border)]">
      <div className="flex items-end gap-2 bg-[rgba(247,240,255,0.04)] border border-[rgba(247,240,255,0.12)] rounded-[14px] px-3 py-2 focus-within:border-[var(--v2-border-focus)] transition-colors">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Ask Chief anything…"
          rows={1}
          disabled={disabled}
          className="flex-1 bg-transparent text-sm text-[var(--v2-text)] placeholder:text-[var(--v2-subtle)] resize-none outline-none leading-relaxed"
          style={{ minHeight: '24px', maxHeight: '160px' }}
        />
        <Button
          variant="solid"
          size="xs"
          onClick={submit}
          disabled={!value.trim() || disabled}
          className="flex-shrink-0 mb-0.5"
        >
          <SendHorizontal size={12} />
        </Button>
      </div>
      <p className="text-[10px] text-[var(--v2-subtle)] mt-1.5 px-1">Enter to send · Shift+Enter for newline</p>
    </div>
  );
}
