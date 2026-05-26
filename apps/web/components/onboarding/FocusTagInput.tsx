'use client';
import { useState, useRef } from 'react';
import { X } from 'lucide-react';
import { cn } from '@/lib/cn';

const SUGGESTIONS_BY_ROLE: Record<string, string[]> = {
  Founder: ['Building my startup', 'Fundraising', 'Product launch'],
  Student: ['Master thesis', 'Final exams', 'Research paper'],
  Freelancer: ['Client projects', 'Growing revenue', 'Portfolio site'],
  Engineer: ['Side project', 'Open source', 'Learning Rust'],
  Creator: ['YouTube channel', 'Newsletter', 'Course launch'],
  Other: ['Personal project', 'Learning new skill', 'Health goals'],
};

interface FocusTagInputProps {
  tags: string[];
  onChange: (tags: string[]) => void;
  roles: string[];
  maxTags?: number;
}

export function FocusTagInput({ tags, onChange, roles, maxTags = 3 }: FocusTagInputProps) {
  const [input, setInput] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const suggestions = Array.from(
    new Set(roles.flatMap(r => SUGGESTIONS_BY_ROLE[r] ?? []))
  ).filter(s => !tags.includes(s)).slice(0, 6);

  function addTag(value: string) {
    const trimmed = value.trim();
    if (!trimmed || tags.includes(trimmed) || tags.length >= maxTags) return;
    onChange([...tags, trimmed]);
    setInput('');
  }

  function removeTag(tag: string) {
    onChange(tags.filter(t => t !== tag));
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if ((e.key === 'Enter' || e.key === ',') && input.trim()) {
      e.preventDefault();
      addTag(input);
    }
    if (e.key === 'Backspace' && !input && tags.length > 0) {
      removeTag(tags[tags.length - 1]);
    }
  }

  return (
    <div className="space-y-3">
      <div
        onClick={() => inputRef.current?.focus()}
        className="min-h-[44px] flex flex-wrap gap-2 px-3 py-2.5 rounded-[10px] bg-[rgba(247,240,255,0.04)] border border-[rgba(247,240,255,0.12)] focus-within:border-[var(--v2-border-focus)] transition-colors cursor-text"
      >
        {tags.map(tag => (
          <span
            key={tag}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[rgba(138,58,255,0.15)] border border-[rgba(138,58,255,0.30)] text-[var(--v2-text)] text-[12px] font-medium"
          >
            {tag}
            <button
              type="button"
              onClick={e => { e.stopPropagation(); removeTag(tag); }}
              className="text-[var(--v2-muted)] hover:text-[var(--v2-crit)] transition-colors"
            >
              <X size={11} />
            </button>
          </span>
        ))}
        {tags.length < maxTags && (
          <input
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={() => { if (input.trim()) addTag(input); }}
            placeholder={tags.length === 0 ? 'Type a focus and press Enter…' : ''}
            className="flex-1 min-w-[120px] bg-transparent outline-none text-sm text-[var(--v2-text)] placeholder:text-[var(--v2-subtle)]"
          />
        )}
      </div>
      {suggestions.length > 0 && tags.length < maxTags && (
        <div className="space-y-1.5">
          <p className="text-[11px] uppercase tracking-[0.08em] text-[var(--v2-subtle)]">Suggestions</p>
          <div className="flex flex-wrap gap-2">
            {suggestions.map(s => (
              <button
                key={s}
                type="button"
                onClick={() => addTag(s)}
                className="px-2.5 py-1 rounded-full border border-[rgba(247,240,255,0.12)] bg-[rgba(247,240,255,0.04)] text-[var(--v2-muted)] text-[12px] hover:border-[rgba(138,58,255,0.35)] hover:text-[var(--v2-text)] hover:bg-[rgba(138,58,255,0.08)] transition-all"
              >
                + {s}
              </button>
            ))}
          </div>
        </div>
      )}
      <p className={cn(
        'text-[11px]',
        tags.length >= maxTags ? 'text-[var(--v2-muted)]' : 'text-[var(--v2-subtle)]'
      )}>
        {tags.length}/{maxTags} focuses added
      </p>
    </div>
  );
}
